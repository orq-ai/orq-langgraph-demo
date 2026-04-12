"""Shared scorers that invoke orq.ai evaluators from the evaluatorq pipeline.

These wrap the `POST /v2/evaluators/{id}/invoke` endpoint so that evaluators
created in the orq.ai Studio (via `make setup-workspace` or the Studio UI)
can be reused as evaluatorq scorers. This keeps the Studio as the source of
truth — tweak the evaluator code/prompt in the Studio, no client-side change
needed for the eval pipeline to pick it up.
"""

import os
from typing import Any, Dict

import httpx
from evaluatorq import EvaluationResult

API_BASE = "https://api.orq.ai/v2"


async def _invoke_orq_evaluator(
    evaluator_id: str,
    output: str,
    query: str = "",
    reference: str = "",
) -> Dict[str, Any]:
    """POST to /v2/evaluators/{id}/invoke and return the parsed JSON body.

    Raises `httpx.HTTPStatusError` on non-2xx responses.
    """
    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        raise RuntimeError("ORQ_API_KEY is not set")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/evaluators/{evaluator_id}/invoke",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "output": output,
                "query": query,
                "reference": reference,
            },
        )
        response.raise_for_status()
        return response.json()


async def source_citations_scorer(params: Dict[str, Any]) -> EvaluationResult:
    """Check if the agent response contains at least one source URL.

    Wraps the `source-citations-present` Python evaluator managed in the
    orq.ai Studio. Returns PASS if the evaluator returned True, FAIL otherwise.

    Reads `ORQ_SOURCE_CITATIONS_EVALUATOR_ID` from env. Skips silently (as a
    PASS) if the ID is not configured so the eval pipeline still runs.
    """
    evaluator_id = os.environ.get("ORQ_SOURCE_CITATIONS_EVALUATOR_ID")
    if not evaluator_id:
        return EvaluationResult(
            value="PASS",
            pass_=True,
            explanation="ORQ_SOURCE_CITATIONS_EVALUATOR_ID not set — scorer skipped",
        )

    output = params["output"]
    response_text = output.get("response", "") if isinstance(output, dict) else str(output)
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
        )
    except Exception as e:
        return EvaluationResult(
            value="FAIL",
            pass_=False,
            explanation=f"evaluator invocation failed: {e}",
        )

    # Response shape is {"type": "boolean", "value": true/false}
    # or for LLM-wrapped evaluators: {"value": {"value": true/false, "explanation": "..."}}
    value = body.get("value")
    explanation = ""
    if isinstance(value, dict):
        explanation = value.get("explanation", "") or ""
        value = value.get("value")

    if value is True:
        return EvaluationResult(
            value="PASS", pass_=True, explanation=explanation or "source URL found"
        )
    if value is False:
        return EvaluationResult(
            value="FAIL",
            pass_=False,
            explanation=explanation or "no source URL in the response",
        )

    return EvaluationResult(
        value="FAIL",
        pass_=False,
        explanation=f"unexpected evaluator response shape: {body}",
    )
