"""Define the state structures for the agent.

`State` is a `TypedDict` (LangGraph's recommended state type) rather than a
dataclass. Dataclasses don't serialize cleanly through LangChain's OTEL
tracer — span inputs/outputs show up as `{"lc": 1, "type": "not_implemented",
"id": ["assistant", "state", ...]}` in the orq.ai Studio Traces view.
TypedDicts round-trip through the standard JSON serializer without that
stub, so every node's real input/output is visible in the trace tree.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Any, Dict, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from pydantic import BaseModel, Field


class Router(BaseModel):
    """Router model for query classification (used as LLM structured output)."""

    type: str = Field(description="The type of query: 'on_topic', 'more-info', or 'general'")
    logic: str = Field(description="The reasoning for the classification")


class InputState(TypedDict):
    """Initial state shape — what the user sends in."""

    messages: Annotated[Sequence[AnyMessage], add_messages]


class State(InputState, total=False):
    """Full agent state. Fields beyond `messages` are optional (`total=False`)
    so nodes don't have to populate every key on every return.

    - `is_last_step` — managed by LangGraph; True when recursion_limit is about
      to trip.
    - `safety` — dict form of the input safety check result, with
      `safety_assessment` and `unsafe_categories` keys.
    - `router` — classification from `analyze_and_route_query`, with `type`
      and `logic` keys.

    Note: KB search hits are NOT stored in state. The `search_documents` /
    `search_in_document` tools use LangChain's `content_and_artifact`
    response format, so structured `SearchResult` objects ride on each
    `ToolMessage.artifact` field. Anything that wants the structured hits
    (eval scorers, the Chainlit PDF previewer) walks `state["messages"]`
    and reads `artifact` off the ToolMessages it finds.
    """

    is_last_step: IsLastStep
    safety: Optional[Dict[str, Any]]
    router: Optional[Dict[str, str]]
