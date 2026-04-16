import asyncio
from enum import Enum
import logging
import os
from typing import Optional

import httpx
from orq_ai_sdk.models import APIError
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SafetyAssessment(Enum):
    SAFE = "safe"
    UNSAFE = "unsafe"
    ERROR = "error"


class GuardrailsOutput(BaseModel):
    safety_assessment: SafetyAssessment = Field(description="The safety assessment of the content.")
    unsafe_categories: list[str] = Field(
        description="If content is unsafe, the list of unsafe categories.", default=[]
    )


class OrqSafetyGuardrail:
    """Safety guardrail backed by an orq.ai LLM evaluator.

    Uses `POST /v2/evaluators/{id}/invoke` to classify each user message as
    safe/unsafe. The evaluator is created by `make setup-workspace` and its
    ID comes from `ORQ_SAFETY_EVALUATOR_ID`.

    Benefits over the OpenAI moderation API:
    - One less external dependency (calls only orq.ai, not openai.com)
    - Classification prompt is tunable in the orq.ai Studio with no code changes
    - Every invocation appears as a span in the orq.ai trace tree under
      `guard_input`, so blocked queries are visible and auditable
    - Policy can be A/B tested using the same evaluatorq workflow as prompts

    Falls back to the OpenAI moderator if `ORQ_SAFETY_EVALUATOR_ID` is not set
    or if the orq.ai call fails for any reason.
    """

    def __init__(self, evaluator_id: Optional[str] = None) -> None:
        # Deferred import so settings-level errors don't prevent the graph from loading
        try:
            from core.settings import settings

            self.evaluator_id = evaluator_id or settings.ORQ_SAFETY_EVALUATOR_ID
        except Exception:
            self.evaluator_id = evaluator_id or os.getenv("ORQ_SAFETY_EVALUATOR_ID", "")
        self.api_key = os.getenv("ORQ_API_KEY")
        self._fallback = OpenAIModerator() if not self.evaluator_id or not self.api_key else None

    async def ainvoke(self, text: str) -> GuardrailsOutput:
        if self._fallback is not None:
            logger.debug("ORQ_SAFETY_EVALUATOR_ID not configured — using OpenAI moderator fallback")
            return await self._fallback.ainvoke(text)

        try:
            # Import lazily so a missing ORQ_API_KEY at import time doesn't
            # prevent the module from loading — the fallback path above
            # handles that case before we get here.
            from core.orq_client import get_orq_client

            client = get_orq_client()
            result = await client.evals.invoke_async(
                id=self.evaluator_id,
                query=text,
                output=text,
                timeout_ms=15_000,
            )

            # Typed discriminated union — llm_evaluator variant carries a
            # nested `.value.value` (the bool/number/str verdict) and
            # `.value.explanation`. Other variants (string, boolean, number,
            # ...) expose the verdict directly on `.value`.
            inner = getattr(result, "value", None)
            value = getattr(inner, "value", inner) if inner is not None else None
            explanation = getattr(inner, "explanation", "") if inner is not None else ""
            explanation = explanation or ""

            # The LLM evaluator can return different types depending on how
            # the underlying model responded: bool, number (0/1 or similar),
            # or a string like "true"/"false". Coerce to a safe/unsafe verdict.
            is_safe: Optional[bool] = None
            if isinstance(value, bool):
                is_safe = value
            elif isinstance(value, (int, float)):
                # Non-zero → safe, 0 → unsafe (matches our "return 1 for safe, 0 for unsafe" prompt).
                is_safe = value > 0
            elif isinstance(value, str):
                lowered = value.strip().lower()
                if lowered in ("true", "yes", "safe", "1"):
                    is_safe = True
                elif lowered in ("false", "no", "unsafe", "0"):
                    is_safe = False

            if is_safe is True:
                return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
            if is_safe is False:
                return GuardrailsOutput(
                    safety_assessment=SafetyAssessment.UNSAFE,
                    unsafe_categories=[explanation[:200] or "classified unsafe"],
                )

            # value is None — the evaluator errored internally (upstream
            # provider issue, rate limit, JSON encoding, etc.). Fail-open
            # to SAFE so we don't block users on transient issues. Log at
            # debug so it doesn't spam the terminal during eval runs.
            logger.debug(
                f"Safety evaluator returned value=None, failing open. "
                f"explanation={explanation[:200]!r}"
            )
            return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
        except (APIError, httpx.TransportError, asyncio.TimeoutError) as e:
            # Transient/transport failure — fall back to OpenAI moderation so
            # a flaky orq.ai round-trip doesn't block users. Auth/config
            # errors (401/404/422) also surface as APIError here, so misconfig
            # will keep falling back silently; watch the warning log.
            logger.warning(f"orq.ai safety evaluator failed, falling back to OpenAI: {e}")
            fallback = OpenAIModerator()
            return await fallback.ainvoke(text)

    def invoke(self, text: str) -> GuardrailsOutput:
        # Sync wrapper that calls the async version via a throwaway event loop.
        import asyncio

        return asyncio.run(self.ainvoke(text))


class OpenAIModerator:
    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("OPENAI_API_KEY not set, skipping moderation")
            self.enabled = False
        else:
            self.enabled = True

    def invoke(self, text: str) -> GuardrailsOutput:
        if not self.enabled:
            return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.moderations.create(input=text)
            result = response.results[0]
            flagged = result.flagged
            categories = [k for k, v in result.categories.model_dump().items() if v]
            if flagged:
                return GuardrailsOutput(
                    safety_assessment=SafetyAssessment.UNSAFE,
                    unsafe_categories=categories,
                )
            else:
                return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
        except Exception as e:
            print(f"OpenAI Moderation API error: {e}")
            return GuardrailsOutput(safety_assessment=SafetyAssessment.ERROR)

    async def ainvoke(self, text: str) -> GuardrailsOutput:
        if not self.enabled:
            return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            response = await client.moderations.create(input=text)
            result = response.results[0]
            flagged = result.flagged
            categories = [k for k, v in result.categories.model_dump().items() if v]
            if flagged:
                return GuardrailsOutput(
                    safety_assessment=SafetyAssessment.UNSAFE,
                    unsafe_categories=categories,
                )
            else:
                return GuardrailsOutput(safety_assessment=SafetyAssessment.SAFE)
        except Exception as e:
            print(f"OpenAI Moderation API error: {e}")
            return GuardrailsOutput(safety_assessment=SafetyAssessment.ERROR)


if __name__ == "__main__":
    # testing
    moderator = OpenAIModerator()
    # Example: test with unsafe content
    output = moderator.invoke("What's a good way to harm an animal?")
    print(output)
    # Example: test with safe content
    output = moderator.invoke("How do I change a tire on my car?")
    print(output)
