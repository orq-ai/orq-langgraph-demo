"""Shared scorers that invoke orq.ai evaluators from the evaluatorq pipeline.

These wrap the `POST /v2/evaluators/{id}/invoke` endpoint so that evaluators
created in the orq.ai Studio (via `make setup-workspace` or the Studio UI)
can be reused as evaluatorq scorers. This keeps the Studio as the source of
truth — tweak the evaluator code/prompt in the Studio, no client-side change
needed for the eval pipeline to pick it up.
"""

import os
from typing import Any, Dict, List

import httpx
from evaluatorq import EvaluationResult

API_BASE = "https://api.orq.ai/v2"


async def _invoke_orq_evaluator(
    evaluator_id: str,
    output: str,
    query: str = "",
    reference: str = "",
    retrievals: List[str] | None = None,
) -> Dict[str, Any]:
    """POST to /v2/evaluators/{id}/invoke and return the parsed JSON body.

    Raises `httpx.HTTPStatusError` on non-2xx responses.
    """
    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        raise RuntimeError("ORQ_API_KEY is not set")
    payload: Dict[str, Any] = {
        "output": output,
        "query": query,
        "reference": reference,
    }
    if retrievals is not None:
        payload["retrievals"] = retrievals
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{API_BASE}/evaluators/{evaluator_id}/invoke",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        return response.json()


def _parse_bool_result(body: Dict[str, Any]) -> tuple[bool | None, str]:
    """Normalize the various response shapes the evaluator API returns.

    Returns (is_true, explanation). `is_true` can be None if the shape is
    unrecognized.
    """
    inner = body.get("value") or {}
    value = inner.get("value") if isinstance(inner, dict) else inner
    explanation = inner.get("explanation", "") if isinstance(inner, dict) else ""

    # Coerce bool / numeric / string → boolean verdict
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
            body = await _invoke_orq_evaluator(
                evaluator_id,
                output=response_text,
                query=query,
                retrievals=retrievals,
            )
        except Exception as e:
            return EvaluationResult(
                value=False,
                pass_=False,
                explanation=f"{name} evaluator invocation failed: {e}",
            )

        is_true, explanation = _parse_bool_result(body)
        if is_true is True:
            return EvaluationResult(
                value=True, pass_=True, explanation=explanation or positive_label
            )
        if is_true is False:
            return EvaluationResult(
                value=False, pass_=False, explanation=explanation or negative_label
            )
        return EvaluationResult(
            value=False,
            pass_=False,
            explanation=f"{name}: unexpected evaluator response shape: {body}",
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
