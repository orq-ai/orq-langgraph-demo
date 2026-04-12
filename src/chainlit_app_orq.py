#!/usr/bin/env python3
"""Chainlit UI that invokes the managed orq.ai Agent (Approach B).

This is the companion to `chainlit_app.py` (Approach A — LangGraph).
Both entry points serve the same UI and target the same Knowledge Base,
but this one lets the orq.ai Studio orchestrate the conversation:
instructions, tool calls (KB retrieve + query), and guardrails are all
configured in the Studio rather than in Python.

Run with:

    make run-orq-agent
    # or
    uv run chainlit run src/chainlit_app_orq.py

See `docs/comparing-approaches.md` for the side-by-side comparison.
"""

import logging
from pathlib import Path

from assistant.tracing import setup_tracing

setup_tracing()

import chainlit as cl

from assistant.utils import load_starters_from_csv
from core.settings import settings
from orq_agent import invoke_managed_agent

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("langchain_core.callbacks.manager").setLevel(logging.ERROR)


@cl.set_starters
async def set_starters():
    """Set sample conversation starter messages."""
    try:
        conversation_starters = load_starters_from_csv(settings.STARTERS_CSV_PATH)
        logger.info(f"Loaded {len(conversation_starters)} starter messages")
        return [
            cl.Starter(label=item["label"], message=item["message"])
            for item in conversation_starters
        ]
    except Exception as e:
        logger.error(f"Error loading starters: {e}")
        return [
            cl.Starter(
                label="Toyota warranty",
                message="What is the Toyota warranty for Europe?",
            ),
        ]


@cl.on_chat_start
async def start():
    """Initialize the chat session.

    Unlike the LangGraph entry point, there's no local agent state to
    initialize — the managed agent handles its own conversation memory
    through orq.ai Memory Stores when configured.
    """
    logger.info("Starting new chat session (managed orq.ai Agent)")
    await cl.Message(
        content=(
            "👋 You're chatting with the **managed orq.ai Agent** version of this assistant.\n\n"
            "This agent is configured entirely in the orq.ai Studio — "
            "instructions, tools, and Knowledge Base wiring live there, "
            "not in this repo.\n\n"
            "Try asking a question about warranties, manuals, or contracts. "
            "(Sales data queries aren't wired up in this version — use "
            "`make run` for the LangGraph version that handles both.)"
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message):
    """Forward the user's question to the managed orq.ai Agent."""
    thinking = cl.Message(content="")
    await thinking.send()

    try:
        reply = await invoke_managed_agent(message.content)
    except Exception as e:
        logger.error(f"Managed agent invocation failed: {e}")
        thinking.content = (
            f"❌ **Agent invocation failed**: `{type(e).__name__}: {e}`\n\n"
            f"Check that `ORQ_API_KEY` and `ORQ_MANAGED_AGENT_KEY` are set, "
            f"and that the agent exists on orq.ai. Run `make setup-workspace` to bootstrap."
        )
        await thinking.update()
        return

    thinking.content = reply
    await thinking.update()


if __name__ == "__main__":
    logger.info("Starting Chainlit app (managed orq.ai Agent)...")
    cl.run()
