"""Tests for the --strict CI gate in run_evals.py.

Verifies that tool_accuracy_scorer produces pass_=True/False correctly,
and that the evaluatorq check_pass_failures function (which drives sys.exit)
responds to those values.
"""

import asyncio
import os
import sys

# Make evals/ importable
_EVALS_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../evals"))
if _EVALS_ROOT not in sys.path:
    sys.path.insert(0, _EVALS_ROOT)

_SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from _shared import tool_accuracy_scorer  # noqa: E402
from evaluatorq import DataPoint, EvaluationResult  # noqa: E402
from evaluatorq.evaluatorq import check_pass_failures  # noqa: E402
from evaluatorq.types import DataPointResult, EvaluatorScore, JobResult  # noqa: E402


def make_result(pass_value: bool) -> list[DataPointResult]:
    """Build a minimal EvaluatorqResult with a single tool-accuracy score."""
    return [
        DataPointResult(
            data_point=DataPoint(inputs={"question": "test"}),
            job_results=[
                JobResult(
                    job_name="test-job",
                    output={},
                    error=None,
                    evaluator_scores=[
                        EvaluatorScore(
                            evaluator_name="tool-accuracy",
                            score=EvaluationResult(value=pass_value, pass_=pass_value),
                            error=None,
                        )
                    ],
                )
            ],
            error=None,
        )
    ]


class TestToolAccuracyScorer:
    """tool_accuracy_scorer unit tests — no agent, no API calls."""

    def _run(self, expected: list[str], actual: list[str]) -> EvaluationResult:
        params = {
            "data": None,
            "output": {"expected_tools": expected, "tools_called": actual},
        }
        return asyncio.run(tool_accuracy_scorer(params))

    def test_perfect_match_passes(self):
        result = self._run(["get_top_dishes"], ["get_top_dishes"])
        assert result.pass_ is True

    def test_superset_passes(self):
        """Agent called extra tools — still counts as pass."""
        result = self._run(["get_top_dishes"], ["get_top_dishes", "search_knowledge_base"])
        assert result.pass_ is True

    def test_missing_expected_tool_fails(self):
        result = self._run(["get_top_dishes"], ["search_knowledge_base"])
        assert result.pass_ is False

    def test_no_tools_called_fails(self):
        result = self._run(["get_top_dishes"], [])
        assert result.pass_ is False

    def test_empty_expected_passes(self):
        """No expected tools — any call is fine."""
        result = self._run([], ["search_knowledge_base"])
        assert result.pass_ is True


class TestStrictGate:
    """check_pass_failures drives sys.exit(1) in --strict mode."""

    def test_all_pass_no_failures(self):
        results = make_result(pass_value=True)
        assert check_pass_failures(results) is False

    def test_any_fail_detected(self):
        results = make_result(pass_value=False)
        assert check_pass_failures(results) is True

    def test_empty_results_no_failures(self):
        assert check_pass_failures([]) is False
