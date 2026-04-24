"""Alternative entry point: invoke a managed orq.ai Agent instead of the LangGraph graph.

This is Approach B of the "LangGraph vs managed Agent" comparison (see
`comparing-approaches.md`). It talks to the same Knowledge Base and
shares the same project as the LangGraph agent, but the orchestration,
tool calling, and system prompt live entirely inside the orq.ai Studio
rather than in Python code.

Use this module as a drop-in alternative to `assistant.graph.graph`:

    from orq_agent import invoke_managed_agent

    reply = await invoke_managed_agent("What is our refund policy for late deliveries?")
    print(reply)

Required env var:
    ORQ_MANAGED_AGENT_KEY — bootstrap via `make setup-workspace`
"""

import os
from typing import Optional

from orq_ai_sdk.models.createagentresponse import CreateAgentResponse
from orq_ai_sdk.models.textpart import TextPart

from core.orq_client import get_orq_client

INVOKE_TIMEOUT_MS = 300_000


def _extract_reply(response: CreateAgentResponse) -> str:
    """Pull the agent's final text reply out of the responses API result.

    Iterates output messages in reverse to find the last agent turn,
    then concatenates all TextPart.text fields.
    """
    for msg in reversed(response.output or []):
        if msg.role == "agent":
            texts = [part.text for part in msg.parts if isinstance(part, TextPart)]
            text = "\n".join(t for t in texts if t)
            if text:
                return text
    return ""


async def invoke_managed_agent(message: str, agent_key: Optional[str] = None) -> str:
    """Invoke the managed orq.ai Agent and return its final text reply.

    Args:
        message: The user's question.
        agent_key: Override the agent key from env. Defaults to
            `ORQ_MANAGED_AGENT_KEY`.

    Returns:
        The agent's final text reply as a string.
    """
    key = agent_key or os.environ.get("ORQ_MANAGED_AGENT_KEY")
    if not key:
        raise RuntimeError("ORQ_MANAGED_AGENT_KEY is not set. Run `make setup-workspace` first.")

    client = get_orq_client()
    response = await client.agents.responses.create_async(
        agent_key=key,
        message={
            "role": "user",
            "parts": [{"kind": "text", "text": message}],
        },
        background=False,
        timeout_ms=INVOKE_TIMEOUT_MS,
    )

    return _extract_reply(response)


def invoke_managed_agent_sync(message: str, agent_key: Optional[str] = None) -> str:
    """Synchronous wrapper around `invoke_managed_agent`. Useful for scripts."""
    import asyncio

    return asyncio.run(invoke_managed_agent(message, agent_key=agent_key))


if __name__ == "__main__":
    import sys

    question = (
        sys.argv[1] if len(sys.argv) > 1 else "What is our refund policy for late deliveries?"
    )
    print(f"Q: {question}\n")
    print("A:", invoke_managed_agent_sync(question))
