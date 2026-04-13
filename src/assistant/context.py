"""Define the configurable parameters for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
import os
from typing import Annotated

from core.settings import settings

from . import prompts


@dataclass
class Context:
    """The context for the agent."""

    system_prompt: str = field(
        default_factory=prompts.get_system_prompt,
        metadata={
            "description": "The system prompt to use for the agent's interactions. "
            "This prompt sets the context and behavior for the agent. "
            "Fetched from orq.ai when ORQ_SYSTEM_PROMPT_ID is set, "
            "otherwise falls back to the hardcoded SYSTEM_PROMPT."
        },
    )

    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default=settings.DEFAULT_MODEL,
        metadata={
            "description": "The name of the language model to use for the agent's main interactions. "
            "Should be in the form: provider/model-name."
        },
    )

    max_search_results: int = field(
        default=settings.MAX_SEARCH_RESULTS,
        metadata={
            "description": "The maximum number of search results to return for each search query."
        },
    )

    router_system_prompt: str = field(
        default=prompts.ROUTER_SYSTEM_PROMPT,
        metadata={"description": "System prompt for query classification and routing."},
    )

    more_info_system_prompt: str = field(
        default=prompts.MORE_INFO_SYSTEM_PROMPT,
        metadata={"description": "System prompt for asking users for more information."},
    )

    general_system_prompt: str = field(
        default=prompts.GENERAL_SYSTEM_PROMPT,
        metadata={"description": "System prompt for handling off-topic queries."},
    )

    def __post_init__(self) -> None:
        """Fetch env vars for attributes that were not passed as args."""
        for f in fields(self):
            if not f.init:
                continue

            if getattr(self, f.name) == f.default:
                setattr(self, f.name, os.environ.get(f.name.upper(), f.default))
