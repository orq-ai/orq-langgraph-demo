#!/usr/bin/env python3
"""
A/B test two system prompt versions against the evaluation dataset.

Runs the same agent twice — once with the default system prompt
(ORQ_SYSTEM_PROMPT_ID) and once with variant B (ORQ_SYSTEM_PROMPT_ID_VARIANT_B)
— and prints a side-by-side comparison of the scorer results. Results sync
to orq.ai Studio as a single experiment with two job variants.

Usage:
    make evals-compare-prompts
    # or
    uv run python evals/run_prompt_experiment.py

Requires in the environment:
    - ORQ_API_KEY
    - ORQ_PROJECT_NAME
    - ORQ_SYSTEM_PROMPT_ID             (variant A)
    - ORQ_SYSTEM_PROMPT_ID_VARIANT_B   (variant B)

Run `make setup-workspace` to create both variants if they don't exist.
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, List

from dotenv import load_dotenv

# Add the project root to Python path so we can import the assistant module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, project_root)

# Load env and set up OTEL tracing BEFORE importing langchain/evaluatorq
load_dotenv()
from assistant.tracing import setup_tracing  # noqa: E402

setup_tracing()

from evaluatorq import DataPoint, EvaluationResult, evaluatorq, job  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402

from assistant.prompts import fetch_prompt_by_id  # noqa: E402
from core.settings import settings  # noqa: E402
from orq_scorers import source_citations_scorer  # noqa: E402


# Filled in by main() before the jobs run
_VARIANT_A_PROMPT: str = ""
_VARIANT_B_PROMPT: str = ""


def extract_tools_from_messages(messages: List[Any]) -> List[str]:
    """Extract tool names from LangGraph messages."""
    tools_called = []
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


async def _run_agent_with_prompt(
    data: DataPoint, row: int, variant_label: str, system_prompt: str
) -> dict:
    """Shared inner body: run the agent with a specific system prompt string."""
    from assistant.context import Context
    from assistant.graph import graph

    question = data.inputs["question"]
    category = data.inputs.get("category", "unknown")

    raw_tools = data.inputs.get("expected_tools", [])
    expected_tools = json.loads(raw_tools) if isinstance(raw_tools, str) else raw_tools

    print(f"[{row}][{variant_label}] {question}")

    # Explicit system_prompt on the Context overrides the cached default.
    context = Context(system_prompt=system_prompt)
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=question)]}, context=context
    )

    response = result["messages"][-1].content
    tools_called = extract_tools_from_messages(result["messages"])

    return {
        "variant": variant_label,
        "response": response,
        "tools_called": tools_called,
        "expected_tools": expected_tools,
        "category": category,
    }


@job("hybrid-data-agent-variant-a")
async def variant_a_job(data: DataPoint, row: int):
    """Run the agent using the default system prompt (variant A)."""
    return await _run_agent_with_prompt(data, row, "A", _VARIANT_A_PROMPT)


@job("hybrid-data-agent-variant-b")
async def variant_b_job(data: DataPoint, row: int):
    """Run the agent using the concise system prompt (variant B)."""
    return await _run_agent_with_prompt(data, row, "B", _VARIANT_B_PROMPT)


async def tool_accuracy_scorer(params) -> EvaluationResult:
    """PASS if all expected tools were called (extra tools are allowed)."""
    output = params["output"]
    expected_tools = set(output.get("expected_tools", []))
    actual_tools = set(output.get("tools_called", []))

    expected_present = expected_tools.issubset(actual_tools)

    if expected_tools == actual_tools:
        return EvaluationResult(
            value="PASS", pass_=True, explanation="Perfect tool match"
        )

    if expected_present:
        extra = len(actual_tools) - len(expected_tools)
        return EvaluationResult(
            value="PASS",
            pass_=True,
            explanation=f"All {len(expected_tools)} expected tools present (+{extra} extra)",
        )

    if expected_tools.intersection(actual_tools):
        overlap = len(expected_tools.intersection(actual_tools))
        return EvaluationResult(
            value="FAIL",
            pass_=False,
            explanation=f"Partial match: {overlap}/{len(expected_tools)} expected tools present",
        )

    return EvaluationResult(
        value="FAIL", pass_=False, explanation="No expected tools present"
    )


async def category_accuracy_scorer(params) -> EvaluationResult:
    """PASS if all expected tools were called, annotated with the category."""
    output = params["output"]
    category = output.get("category", "unknown")
    expected_tools = set(output.get("expected_tools", []))
    actual_tools = set(output.get("tools_called", []))

    expected_present = expected_tools.issubset(actual_tools)
    if expected_present:
        return EvaluationResult(
            value="PASS",
            pass_=True,
            explanation=f"Category '{category}': all expected tools present",
        )

    overlap = len(expected_tools.intersection(actual_tools)) if expected_tools else 0
    return EvaluationResult(
        value="FAIL",
        pass_=False,
        explanation=f"Category '{category}': {overlap}/{len(expected_tools)} tools matched",
    )


def load_datapoints_from_file() -> List[DataPoint]:
    """Load DataPoints from the local JSONL file."""
    filename = os.path.join(
        os.path.dirname(__file__), "datasets/tool_calling_evals.jsonl"
    )
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Dataset file not found: {filename}")

    datapoints = []
    with open(filename, "r") as f:
        for line in f:
            if line.strip():
                ex = json.loads(line)
                datapoints.append(DataPoint(inputs=ex["inputs"]))
    return datapoints


async def run_experiment() -> None:
    """Fetch both prompt variants and run the A/B experiment."""
    global _VARIANT_A_PROMPT, _VARIANT_B_PROMPT

    prompt_id_a = settings.ORQ_SYSTEM_PROMPT_ID
    prompt_id_b = settings.ORQ_SYSTEM_PROMPT_ID_VARIANT_B

    if not prompt_id_a or not prompt_id_b:
        print(
            "Error: ORQ_SYSTEM_PROMPT_ID and ORQ_SYSTEM_PROMPT_ID_VARIANT_B must both be set.\n"
            "Run `make setup-workspace` to create them."
        )
        sys.exit(1)

    print("Hybrid Data Agent — Prompt A/B Experiment")
    print("=" * 50)
    print(f"Variant A: {prompt_id_a}")
    print(f"Variant B: {prompt_id_b}")

    _VARIANT_A_PROMPT = fetch_prompt_by_id(prompt_id_a)
    _VARIANT_B_PROMPT = fetch_prompt_by_id(prompt_id_b)
    print(f"  A length: {len(_VARIANT_A_PROMPT)} chars")
    print(f"  B length: {len(_VARIANT_B_PROMPT)} chars")
    print()

    data = load_datapoints_from_file()
    print(f"Loaded {len(data)} datapoints from local file")
    print("Starting A/B evaluation...\n")

    await evaluatorq(
        "hybrid-data-agent-prompt-ab",
        data=data,
        jobs=[variant_a_job, variant_b_job],
        evaluators=[
            {"name": "tool-accuracy", "scorer": tool_accuracy_scorer},
            {"name": "category-accuracy", "scorer": category_accuracy_scorer},
            {"name": "source-citations", "scorer": source_citations_scorer},
        ],
        path=settings.ORQ_PROJECT_NAME,
        description="A/B test: default vs concise system prompt",
    )

    print("\nExperiment complete.")
    print("Results available in orq.ai Studio: https://my.orq.ai/experiments")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an A/B experiment comparing two system prompt versions",
    )
    parser.parse_args()  # no args yet, but keep parser for --help

    if not os.environ.get("ORQ_API_KEY"):
        print("Error: ORQ_API_KEY is not set. Add it to .env first.")
        return 1

    try:
        asyncio.run(run_experiment())
        return 0
    except KeyboardInterrupt:
        print("\nExperiment cancelled by user")
        return 1
    except Exception as e:
        print(f"Experiment failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
