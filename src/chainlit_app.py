#!/usr/bin/env python3
"""
Chainlit UI for the Hybrid Data Agent.

This is the Chainlit-based web interface for the LangGraph agent.
It supports basic multi-turn conversations with the LangGraph agent.

Key features:
- Passes complete message history to LangGraph agent for context-aware responses
- Supports streaming responses from the agent
- Streams the nodes and tool calls from the agent
- Supports PDF display functionality for the documents retrieved
"""

import logging
from pathlib import Path

from assistant.tracing import setup_tracing

setup_tracing()

import chainlit as cl  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langchain_core.runnables import RunnableConfig  # noqa: E402

from assistant import graph as agent  # noqa: E402
from assistant.context import Context  # noqa: E402
from assistant.utils import load_starters_from_csv  # noqa: E402
from core.settings import settings  # noqa: E402

# Noisy third-party loggers (httpx, openai, langchain_core) are quieted by
# setup_tracing() in assistant/tracing.py so every entry point inherits the
# same clean defaults.
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Crisp ready banner. Chainlit prints its own startup chatter (watch mode,
# port binding, translation loading) after this — the banner gives the user
# a clean anchor in the terminal before that noise lands.
print("\n" + "─" * 60)
print("  Hybrid Data Agent — LangGraph flow")
print("  Ready → http://localhost:8000")
print("─" * 60 + "\n")


def _extract_search_results_from_messages(messages):
    """Walk the graph output messages and pull SearchResult artifacts.

    The KB tools (`search_documents` / `search_in_document`) use LangChain's
    `response_format="content_and_artifact"`, so each ToolMessage they produce
    has a `.artifact` attribute holding the list of structured SearchResult
    objects (filename, page, chunk, score). We prefer this over re-parsing
    the string content the LLM sees.
    """
    from assistant.models import SearchResult

    search_results = []
    for msg in messages:
        if getattr(msg, "name", None) not in ("search_documents", "search_in_document"):
            continue
        artifact = getattr(msg, "artifact", None)
        if isinstance(artifact, list):
            search_results.extend(a for a in artifact if isinstance(a, SearchResult))
    return search_results


def create_pdf_elements_from_search_results(search_results, docs_dir):
    """Build Chainlit PDF elements from the SearchResult artifacts emitted by
    the KB tools. Deduped by (filename, page)."""
    import chainlit as cl

    pdf_elements = []
    processed_files = set()

    for result in search_results:
        filename = result.filename
        page = result.page

        if not filename.endswith(".pdf"):
            continue

        key = f"{filename}_{page}"
        if key in processed_files:
            continue

        pdf_path = docs_dir / filename
        if not pdf_path.exists():
            # Try case-insensitive search
            for file_path in docs_dir.glob("*.pdf"):
                if file_path.name.lower() == filename.lower():
                    pdf_path = file_path
                    break

        if not pdf_path.exists():
            logger.warning(f"Could not find PDF file: {filename}")
            continue

        try:
            display_name = f"{filename.replace('.pdf', '')} (Page {page})"
            pdf_element = cl.Pdf(name=display_name, display="side", path=str(pdf_path), page=page)
            pdf_elements.append(pdf_element)
            processed_files.add(key)
            logger.info(f"Citing document source: {filename}, page {page}")

        except Exception as e:
            logger.error(f"Failed to create PDF element for {filename}: {e}")

    return pdf_elements


@cl.set_starters
async def set_starters():
    """Set sample conversation starter messages to demonstrate what we can do."""
    try:
        # Load conversation starters from file
        conversation_starters = load_starters_from_csv(settings.STARTERS_CSV_PATH)
        logger.info(
            f"Loaded {len(conversation_starters)} conversation starter messages from csv file"
        )

        # Create Chainlit Starters
        cl_starters = [
            cl.Starter(label=item["label"], message=item["message"])
            for item in conversation_starters
        ]

        return cl_starters

    except Exception as e:
        logger.error(f"Error loading starters from csv file: {e}")
        # Just show something simple if the CSV loading fails
        return [
            cl.Starter(
                label="Toyota vs Lexus warranty",
                message="Compare Toyota vs Lexus warranty",
            ),
            cl.Starter(
                label="RAV4 sales in Germany in 2024",
                message="What was the monthly RAV4 sales in Germany in 2024?",
            ),
        ]


@cl.on_chat_start
async def start():
    """Initialize the RAG agent when a new chat session starts."""
    try:
        logger.info("Starting new chat session")

        # Initialize agent with the system prompt
        context = Context(model=settings.DEFAULT_MODEL)

        logger.info(f"Context initialized with model: {context.model}")

        # Initialize conversation history
        conversation_history = []

        # Store in session for use in message handler
        cl.user_session.set("agent", agent)
        cl.user_session.set("context", context)
        cl.user_session.set("conversation_history", conversation_history)

        logger.info("Agent, context, and conversation history stored in the session successfully")
        logger.info("Chat session initialization complete")

    except Exception as e:
        logger.error(f"Error during chat initialization: {e}")
        await cl.Message(
            content=f"**Error:** Failed to initialize the agent: {e!s}\n\n"
            f"Please refresh the page and try again."
        ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Handle incoming messages with LangGraph streaming."""
    agent = cl.user_session.get("agent")
    context = cl.user_session.get("context")
    conversation_history = cl.user_session.get("conversation_history", [])

    if not agent or not context:
        await cl.Message(content="Agent not initialized. Please refresh the page.").send()
        return

    # Add the new user message to conversation history
    user_message = HumanMessage(content=message.content)
    conversation_history.append(user_message)

    config = {"configurable": {"thread_id": cl.context.session.id}}
    cb = cl.LangchainCallbackHandler()
    final_answer = cl.Message(content="")

    # Keep track of the assistant's response to add to history later
    assistant_response_content = ""

    # Latest message list from the graph, captured from the `values` stream.
    # At the end of the run this holds every message produced, including the
    # ToolMessages whose `.artifact` fields carry the SearchResult structures
    # we need for the PDF previewer.
    latest_messages = []

    # Stream messages and state updates from the graph
    async for chunk in agent.astream(
        {"messages": conversation_history},
        stream_mode=["messages", "values"],
        config=RunnableConfig(callbacks=[cb], **config),
        context=context,
    ):
        if isinstance(chunk, tuple) and len(chunk) == 2:
            stream_type, content = chunk

            if stream_type == "messages":
                msg, metadata = content
                # Stream tokens from the final-response nodes only.
                if (
                    msg.content
                    and not isinstance(msg, HumanMessage)
                    and metadata.get("langgraph_node")
                    in ["call_model", "ask_for_more_info", "respond_to_offtopic_question"]
                ):
                    await final_answer.stream_token(msg.content)
                    assistant_response_content += msg.content

            elif stream_type == "values":
                # Snapshot of the full state after each superstep. We only
                # care about messages — the last snapshot wins.
                state_update = content
                if "messages" in state_update:
                    latest_messages = state_update["messages"]

    # Send the streamed response
    await final_answer.send()

    # Build PDF previews from the KB tool artifacts. We show everything the
    # tools returned — not a relevance-filtered subset — to keep the demo
    # simple. A production UI would apply a reranker / threshold here.
    search_results = _extract_search_results_from_messages(latest_messages)
    if search_results:
        logger.info(f"Found {len(search_results)} KB hits in tool artifacts")

        # Chainlit serves files under `public/` as static assets. Fine for a
        # prototype; production would use blob storage + auth'd URLs.
        docs_dir = Path(__file__).parent.parent / "public" / "docs"

        pdf_elements = create_pdf_elements_from_search_results(search_results, docs_dir)

        if pdf_elements:
            logger.info(f"Created {len(pdf_elements)} PDF elements from retrieved documents")

            # Send follow-up message with PDF elements
            citations = [f"{element.name}" for element in pdf_elements]
            pdf_message = cl.Message(
                content=" ".join(f"{citation}" for citation in citations), elements=pdf_elements
            )
            await pdf_message.send()

    # Add the assistant's response to conversation history
    if assistant_response_content:
        assistant_message = AIMessage(content=assistant_response_content)
        conversation_history.append(assistant_message)

        # Update the conversation history in the session
        cl.user_session.set("conversation_history", conversation_history)

        logger.info(f"Updated conversation history. Total messages: {len(conversation_history)}")


@cl.on_stop
async def stop():
    """Clean up when chat stops."""
    logger.info("Chat session ended")


if __name__ == "__main__":
    logger.info("Starting Chainlit app...")
    cl.run()
