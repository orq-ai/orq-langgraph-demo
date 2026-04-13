"""Shared helpers for the evaluatorq pipelines.

Both `run_evals.py` (single variant) and its A/B mode use the same agent
invocation and the same local scorers — they only differ in how many
prompt variants are being run. This module is the common ground so the
entry point stays a thin argparse shim.
"""

import json
import os
import sys
from typing import Any, List, Optional

from evaluatorq import DataPoint, EvaluationResult, job
from langchain_core.messages import HumanMessage

# Make `src/assistant/*` importable when running as `uv run python evals/...`
_SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)


def extract_tools_from_messages(messages: List[Any]) -> List[str]:
    """Collect unique tool names from the LangGraph message stream."""
    tools_called: List[str] = []
    for message in messages:
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name and tool_name not in tools_called:
                    tools_called.append(tool_name)
        elif hasattr(message, "name") and hasattr(message, "tool_call_id"):
            tool_name = message.name
            if tool_name and tool_name not in tools_called:
                tools_called.append(tool_name)
    return tools_called


def extract_tool_outputs_from_messages(messages: List[Any]) -> List[str]:
    """Extract every ToolMessage's content, labeled with the tool name.

    Used as `retrievals` for the grounding / hallucination / source-citations
    scorers so the evaluators see KB chunks AND SQL query results — anything
    the agent grounded its answer on — not just KB documents.
    """
    outputs: List[str] = []
    for message in messages:
        if not (hasattr(message, "name") and hasattr(message, "tool_call_id")):
            continue
        content = getattr(message, "content", None)
        if not content:
            continue
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(
                part.get("text", "") if isinstance(part, dict) else str(part) for part in content
            )
        else:
            text = str(content)
        tool_name = getattr(message, "name", "tool")
        outputs.append(f"[{tool_name}]\n{text}")
    return outputs


async def tool_accuracy_scorer(params) -> EvaluationResult:
    """Local scorer: True iff every expected tool was called (extras allowed).

    Returns booleans so orq.ai Studio color-codes the cells green/red.
    """
    output = params["output"]
    expected_tools = set(output.get("expected_tools", []))
    actual_tools = set(output.get("tools_called", []))

    expected_present = expected_tools.issubset(actual_tools)

    if expected_tools == actual_tools:
        return EvaluationResult(value=True, pass_=True, explanation="Perfect tool match")

    if expected_present:
        extra = len(actual_tools) - len(expected_tools)
        return EvaluationResult(
            value=True,
            pass_=True,
            explanation=f"All {len(expected_tools)} expected tools present (+{extra} extra)",
        )

    if expected_tools.intersection(actual_tools):
        overlap = len(expected_tools.intersection(actual_tools))
        return EvaluationResult(
            value=False,
            pass_=False,
            explanation=f"Partial match: {overlap}/{len(expected_tools)} expected tools present",
        )

    return EvaluationResult(value=False, pass_=False, explanation="No expected tools present")


def load_datapoints_from_file() -> List[DataPoint]:
    """Load DataPoints from the local JSONL dataset."""
    filename = os.path.join(os.path.dirname(__file__), "datasets/tool_calling_evals.jsonl")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Dataset file not found: {filename}")

    datapoints: List[DataPoint] = []
    with open(filename, "r") as f:
        for line in f:
            if line.strip():
                ex = json.loads(line)
                datapoints.append(DataPoint(inputs=ex["inputs"]))
    return datapoints


def make_agent_job(label: str, system_prompt: Optional[str], total_rows: Optional[int] = None):
    """Build an evaluatorq @job that runs the Hybrid Data Agent.

    Single-variant runs use `system_prompt=None`, letting the graph use
    the cached default from `assistant.prompts`. A/B runs pass each
    variant's prompt text so `Context(system_prompt=...)` overrides the
    default per job. `total_rows` is used only for the progress prefix
    (`[i/N]`) — pass it when you know the dataset size, omit otherwise.
    """
    job_name = f"hybrid-data-agent-{label.lower()}"

    @job(job_name)
    async def _job(data: DataPoint, row: int):
        # Imported inside the closure so tracing is set up before these
        # transitively pull in langchain_core.
        from assistant.context import Context
        from assistant.graph import graph

        question = data.inputs["question"]
        category = data.inputs.get("category", "unknown")

        raw_tools = data.inputs.get("expected_tools", [])
        expected_tools = json.loads(raw_tools) if isinstance(raw_tools, str) else raw_tools

        # evaluatorq's `row` is 0-indexed; humans expect 1-indexed.
        counter = f"{row + 1}/{total_rows}" if total_rows else f"{row + 1}"
        print(f"  [{counter}] [{label}] {question}")

        context = Context(system_prompt=system_prompt) if system_prompt else Context()
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=question)]}, context=context
        )

        return {
            "variant": label,
            "response": result["messages"][-1].content,
            "tools_called": extract_tools_from_messages(result["messages"]),
            "expected_tools": expected_tools,
            "category": category,
            "retrievals": extract_tool_outputs_from_messages(result["messages"]),
        }

    return _job
