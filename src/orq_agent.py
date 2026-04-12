"""Alternative entry point: invoke a managed orq.ai Agent instead of the LangGraph graph.

This is Approach B of the "LangGraph vs managed Agent" comparison (see
`docs/comparing-approaches.md`). It talks to the same Knowledge Base and
shares the same project as the LangGraph agent, but the orchestration,
tool calling, and system prompt live entirely inside the orq.ai Studio
rather than in Python code.

Use this module as a drop-in alternative to `assistant.graph.graph`:

    from orq_agent import invoke_managed_agent

    reply = await invoke_managed_agent("What is the Toyota warranty for Europe?")
    print(reply)

Required env var:
    ORQ_MANAGED_AGENT_KEY — bootstrap via `make setup-workspace`
"""

import os
from typing import Any, Dict, Optional

import httpx

API_BASE = "https://api.orq.ai/v2"
INVOKE_TIMEOUT_SECONDS = 300.0


def _extract_text(body: Dict[str, Any]) -> str:
    """Pull the assistant's final text reply out of the agent response body."""
    output = body.get("output")
    if isinstance(output, list) and output:
        first = output[0]
        parts = first.get("parts") if isinstance(first, dict) else None
        if isinstance(parts, list) and parts:
            text = parts[0].get("text") if isinstance(parts[0], dict) else None
            if text:
                return text
    # Fall back — some responses expose `content` directly
    content = body.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("text")
        ]
        if texts:
            return "\n".join(texts)
    return str(body)


async def invoke_managed_agent(
    message: str, agent_key: Optional[str] = None
) -> str:
    """Invoke the managed orq.ai Agent and return its final text reply.

    Args:
        message: The user's question.
        agent_key: Override the agent key from env. Defaults to
            `ORQ_MANAGED_AGENT_KEY`.

    Returns:
        The agent's final text reply as a string.
    """
    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        raise RuntimeError("ORQ_API_KEY is not set")

    key = agent_key or os.environ.get("ORQ_MANAGED_AGENT_KEY")
    if not key:
        raise RuntimeError(
            "ORQ_MANAGED_AGENT_KEY is not set. Run `make setup-workspace` first."
        )

    payload = {
        "agent_key": key,
        "background": False,
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": message}],
        },
    }

    async with httpx.AsyncClient(timeout=INVOKE_TIMEOUT_SECONDS) as client:
        response = await client.post(
            f"{API_BASE}/agents/{key}/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        body = response.json()

    return _extract_text(body)


def invoke_managed_agent_sync(message: str, agent_key: Optional[str] = None) -> str:
    """Synchronous wrapper around `invoke_managed_agent`. Useful for scripts."""
    import asyncio

    return asyncio.run(invoke_managed_agent(message, agent_key=agent_key))


if __name__ == "__main__":
    import sys

    question = sys.argv[1] if len(sys.argv) > 1 else "What is the Toyota warranty for Europe?"
    print(f"Q: {question}\n")
    print("A:", invoke_managed_agent_sync(question))
