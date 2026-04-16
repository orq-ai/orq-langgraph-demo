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

from orq_ai_sdk.models.extendedmessage import ExtendedMessage
from orq_ai_sdk.models.invokeagentop import InvokeAgentA2ATaskResponse, TaskStatusMessage
from orq_ai_sdk.models.textpart import TextPart

from core.orq_client import get_orq_client

INVOKE_TIMEOUT_MS = 300_000


def _join_text_parts(message: ExtendedMessage | TaskStatusMessage) -> str:
    """Concatenate the `text` fields of every TextPart on a message."""
    texts = [part.text for part in message.parts if isinstance(part, TextPart)]
    return "\n".join(t for t in texts if t)


def _extract_reply(response: InvokeAgentA2ATaskResponse) -> str:
    """Pull the agent's final text reply out of the A2A task response.

    The final reply typically lives on `status.message`; if absent, fall
    back to the last `role='agent'` entry in `messages`.
    """
    if response.status.message is not None:
        text = _join_text_parts(response.status.message)
        if text:
            return text

    for message in reversed(response.messages or []):
        if message.role == "agent":
            text = _join_text_parts(message)
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

    # `invoke_async` defaults `configuration.blocking=False`, which returns
    # immediately with only a task ID — no `messages`, no `status.message`.
    # We want the synchronous A2A semantics of the previous REST call, so
    # force blocking=True. The method itself is marked @deprecated in
    # orq_ai_sdk 4.7.x but there's no stable replacement that invokes a
    # managed agent by key — revisit when the SDK offers one.
    client = get_orq_client()
    response = await client.agents.invoke_async(
        key=key,
        message={
            "role": "user",
            "parts": [{"kind": "text", "text": message}],
        },
        configuration={"blocking": True},
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
