"""Shared scorers that invoke orq.ai evaluators from the evaluatorq pipeline.

These wrap the `POST /v2/evaluators/{id}/invoke` endpoint so that evaluators
created in the orq.ai Studio (via `make setup-workspace` or the Studio UI)
can be reused as evaluatorq scorers. This keeps the Studio as the source of
truth — tweak the evaluator code/prompt in the Studio, no client-side change
needed for the eval pipeline to pick it up.
"""

import asyncio
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

from evaluatorq import EvaluationResult
import httpx
from orq_ai_sdk.models import APIError

# Allow `from core.orq_client import ...` when this module is imported from
# an eval script that hasn't already extended sys.path.
sys.path.append(str(Path(__file__).parent.parent / "src"))
from core.orq_client import get_orq_client  # noqa: E402


async def _invoke_orq_evaluator(
    evaluator_id: str,
    output: str,
    query: str = "",
    reference: str = "",
    retrievals: List[str] | None = None,
) -> Any:
    """Invoke the evaluator via `client.evals.invoke_async` and return the
    typed response object (a discriminated union — for LLM evaluators, an
    `InvokeEvalResponseBodyLLM`).
    """
    client = get_orq_client()
    return await client.evals.invoke_async(
        id=evaluator_id,
        query=query,
        output=output,
        reference=reference,
        retrievals=retrievals,
        timeout_ms=60_000,
    )


def _parse_bool_result(result: Any) -> tuple[bool | None, str]:
    """Normalize the various evaluator response variants to (is_true, explanation).

    `is_true` is None if the verdict shape is unrecognized.
    """
    inner = getattr(result, "value", None)
    # For `llm_evaluator`: `inner` is a typed object with `.value` + `.explanation`.
    # For `boolean`/`number`/`string`: `inner` itself carries the primitive.
    value = getattr(inner, "value", inner) if inner is not None else None
    explanation = getattr(inner, "explanation", "") if inner is not None else ""
    explanation = explanation or ""

    if isinstance(value, bool):
        return value, explanation
    if isinstance(value, (int, float)):
        return value > 0, explanation
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "yes", "1", "pass", "passed"):
            return True, explanation
        if lowered in ("false", "no", "0", "fail", "failed"):
            return False, explanation
    return None, explanation


def _make_scorer(env_var: str, name: str, positive_label: str, negative_label: str):
    """Factory for a scorer that invokes an orq.ai evaluator with retrievals.

    The scorer reads the job output's `response` and `retrievals` fields and
    passes them to the evaluator. Skips as PASS (value=True) if the env var
    is unset, so missing configuration doesn't break the eval pipeline.
    """

    async def scorer(params: Dict[str, Any]) -> EvaluationResult:
        evaluator_id = os.environ.get(env_var)
        if not evaluator_id:
            return EvaluationResult(
                value=True,
                pass_=True,
                explanation=f"{env_var} not set — {name} scorer skipped",
            )

        output = params["output"]
        if not isinstance(output, dict):
            return EvaluationResult(
                value=False,
                pass_=False,
                explanation=f"{name}: expected dict output, got {type(output).__name__}",
            )
        response_text = output.get("response", "") or ""
        retrievals = output.get("retrievals") or []
        # Ensure retrievals is a list of strings
        retrievals = [r if isinstance(r, str) else str(r) for r in retrievals]

        query = ""
        data = params.get("data")
        if data is not None:
            try:
                query = data.inputs.get("question", "") or ""
            except AttributeError:
                pass

        try:
            result = await _invoke_orq_evaluator(
                evaluator_id,
                output=response_text,
                query=query,
                retrievals=retrievals,
            )
        except (APIError, httpx.TransportError, asyncio.TimeoutError) as e:
            # Transport/auth/validation errors surface here. Evaluator bugs
            # (500s from the evaluator's own LLM) and misconfiguration
            # (404/401) both get marked fail rather than swallowed — let the
            # eval report show the failure instead of masking it.
            return EvaluationResult(
                value=False,
                pass_=False,
                explanation=f"{name} evaluator invocation failed: {e}",
            )

        is_true, explanation = _parse_bool_result(result)
        if is_true is True:
            return EvaluationResult(
                value=True, pass_=True, explanation=explanation or positive_label
            )
        if is_true is False:
            return EvaluationResult(
                value=False, pass_=False, explanation=explanation or negative_label
            )
        # Don't dump the full Pydantic response into the eval report —
        # LLM-evaluator responses can include reflected user input via
        # `.value.explanation`, and that shows up in published eval reports.
        return EvaluationResult(
            value=False,
            pass_=False,
            explanation=f"{name}: unexpected evaluator response variant: {type(result).__name__}",
        )

    scorer.__name__ = f"{name.replace('-', '_')}_scorer"
    return scorer


grounding_scorer = _make_scorer(
    env_var="ORQ_GROUNDING_EVALUATOR_ID",
    name="response-grounding",
    positive_label="all factual claims supported by retrievals",
    negative_label="at least one claim not supported by retrievals",
)

hallucination_scorer = _make_scorer(
    env_var="ORQ_HALLUCINATION_EVALUATOR_ID",
    name="hallucination-check",
    positive_label="no hallucinations detected",
    negative_label="hallucination detected",
)


source_citations_scorer = _make_scorer(
    env_var="ORQ_SOURCE_CITATIONS_EVALUATOR_ID",
    name="source-citations-present",
    positive_label="source attribution present",
    negative_label="factual claim made without source attribution",
)
