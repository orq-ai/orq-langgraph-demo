#!/usr/bin/env python3
"""
Run evaluation pipeline against the Hybrid Data Agent using orq.ai evaluatorq.

This script runs your Hybrid Data Agent against a dataset
and tracks evaluation metrics via orq.ai experiments.

Usage:
    python run_evaluation_pipeline.py [dataset_id]
    python run_evaluation_pipeline.py --from-file
    python run_evaluation_pipeline.py --help
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv

# Add the project root to Python path so we can import the assistant module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, project_root)

# Load environment variables and set up OTEL tracing BEFORE importing
# langchain/langgraph/evaluatorq so the LangSmith OTEL hooks register correctly
# and produce the full nested LangGraph trace tree in orq.ai.
load_dotenv()
from assistant.tracing import setup_tracing  # noqa: E402

setup_tracing()

from evaluatorq import DataPoint, DatasetIdInput, EvaluationResult, evaluatorq, job  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402

from core.settings import settings  # noqa: E402
from orq_scorers import (  # noqa: E402
    grounding_scorer,
    hallucination_scorer,
    source_citations_scorer,
)


def extract_tools_from_messages(messages: List[Any]) -> List[str]:
    """
    Extract tool names from LangGraph messages.

    Args:
        messages: List of messages from the graph execution result

    Returns:
        List of tool names that were called during the conversation
    """
    tools_called = []

    for message in messages:
        # Check if message has tool_calls attribute (AIMessage with tool calls)
        if hasattr(message, "tool_calls") and message.tool_calls:
            for tool_call in message.tool_calls:
                tool_name = tool_call.get("name", "")
                if tool_name and tool_name not in tools_called:
                    tools_called.append(tool_name)

        # Also check ToolMessage which has a 'name' attribute
        elif hasattr(message, "name") and hasattr(message, "tool_call_id"):
            tool_name = message.name
            if tool_name and tool_name not in tools_called:
                tools_called.append(tool_name)

    return tools_called


def extract_tool_outputs_from_messages(messages: List[Any]) -> List[str]:
    """Extract ToolMessage content strings from the conversation history.

    This captures everything the agent saw as tool results — KB search
    chunks, SQL query results, date/time tool outputs, etc. — labeled by
    tool name so the grounding / hallucination judges can evaluate the
    response against ALL retrieved context, not just KB documents.
    """
    outputs: List[str] = []
    for message in messages:
        # ToolMessage has both `name` and `tool_call_id`
        if not (hasattr(message, "name") and hasattr(message, "tool_call_id")):
            continue
        content = getattr(message, "content", None)
        if not content:
            continue
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            # Multi-part content — concatenate text parts
            text = "\n".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = str(content)
        tool_name = getattr(message, "name", "tool")
        outputs.append(f"[{tool_name}]\n{text}")
    return outputs


@job("hybrid-data-agent")
async def hybrid_data_agent_job(data: DataPoint, row: int):
    """Run the Hybrid Data Agent with a question and return the result."""
    from assistant.context import Context
    from assistant.graph import graph

    question = data.inputs["question"]
    category = data.inputs.get("category", "unknown")

    # expected_tools may be a JSON string (from orq.ai dataset) or a list (from local JSONL)
    raw_tools = data.inputs.get("expected_tools", [])
    expected_tools = json.loads(raw_tools) if isinstance(raw_tools, str) else raw_tools

    print(f"[{row}] Question: {question}")
    print(f"[{row}] Expected tools: {expected_tools}")

    context = Context()
    result = await graph.ainvoke({"messages": [HumanMessage(content=question)]}, context=context)

    response = result["messages"][-1].content
    tools_called = extract_tools_from_messages(result["messages"])

    # Capture retrievals for grounding / hallucination scorers. We use all
    # tool outputs (KB search chunks, SQL query results, etc.) rather than
    # just state.retrieved_documents — this way the evaluator sees every
    # source the agent actually grounded its response in, regardless of
    # whether it came from the KB or SQL.
    retrievals = extract_tool_outputs_from_messages(result["messages"])

    return {
        "response": response,
        "tools_called": tools_called,
        "expected_tools": expected_tools,
        "category": category,
        "retrievals": retrievals,
    }


async def tool_accuracy_scorer(params) -> EvaluationResult:
    """Evaluate tool selection accuracy. Returns a boolean so orq.ai Studio
    color-codes the cell green/red in the experiment view."""
    output = params["output"]
    expected_tools = set(output.get("expected_tools", []))
    actual_tools = set(output.get("tools_called", []))

    # PASS if all expected tools are present (extra tools are OK)
    expected_present = expected_tools.issubset(actual_tools)

    if expected_tools == actual_tools:
        return EvaluationResult(value=True, pass_=True, explanation="Perfect tool match")

    if expected_present:
        extra = len(actual_tools) - len(expected_tools)
        return EvaluationResult(
            value=True,
            pass_=True,
            explanation=f"All {len(expected_tools)} expected tools present (with {extra} additional)",
        )

    if expected_tools.intersection(actual_tools):
        overlap = len(expected_tools.intersection(actual_tools))
        return EvaluationResult(
            value=False,
            pass_=False,
            explanation=f"Partial match: {overlap}/{len(expected_tools)} expected tools present",
        )

    return EvaluationResult(
        value=False, pass_=False, explanation="No expected tools present"
    )


def load_datapoints_from_file() -> List[DataPoint]:
    """Load DataPoints from the local JSONL file."""
    filename = os.path.join(os.path.dirname(__file__), "datasets/tool_calling_evals.jsonl")
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Dataset file not found: {filename}")

    datapoints = []
    with open(filename, "r") as f:
        for line in f:
            if line.strip():
                ex = json.loads(line)
                datapoints.append(DataPoint(inputs=ex["inputs"]))

    return datapoints


async def run_evaluation(dataset_id: str = None, from_file: bool = False):
    """Run evaluation experiment."""

    print("Hybrid Data Agent Evaluation Pipeline (orq.ai)")
    print("=" * 50)

    if from_file:
        data = load_datapoints_from_file()
        print(f"Loaded {len(data)} datapoints from local file")
    elif dataset_id:
        data = DatasetIdInput(dataset_id=dataset_id)
        print(f"Using orq.ai dataset: {dataset_id}")
    else:
        # Default: load from file
        data = load_datapoints_from_file()
        print(f"Loaded {len(data)} datapoints from local file")

    print("Starting evaluation...")

    await evaluatorq(
        "hybrid-data-agent-tool-calling-eval",
        data=data,
        jobs=[hybrid_data_agent_job],
        evaluators=[
            {"name": "tool-accuracy", "scorer": tool_accuracy_scorer},
            {"name": "source-citations", "scorer": source_citations_scorer},
            {"name": "response-grounding", "scorer": grounding_scorer},
            {"name": "hallucination-check", "scorer": hallucination_scorer},
        ],
        path=settings.ORQ_PROJECT_NAME,
    )

    print("\nEvaluation completed!")
    print("Results available in orq.ai Studio: https://my.orq.ai/experiments")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run evaluations against the Hybrid Data Agent using orq.ai evaluatorq",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python run_evaluation_pipeline.py --from-file
  python run_evaluation_pipeline.py <dataset_id>
        """,
    )

    parser.add_argument(
        "dataset_id",
        nargs="?",
        help="orq.ai dataset ID to evaluate against",
    )

    parser.add_argument(
        "--from-file",
        action="store_true",
        help="Load datapoints from the local JSONL file instead of orq.ai",
    )

    return parser.parse_args()


async def main():
    """Main evaluation function."""
    try:
        args = parse_arguments()

        if not os.environ.get("ORQ_API_KEY"):
            print("Warning: ORQ_API_KEY not set. Results will only appear in terminal.")

        await run_evaluation(
            dataset_id=args.dataset_id,
            from_file=args.from_file,
        )
        return 0

    except KeyboardInterrupt:
        print("\nEvaluation cancelled by user")
        return 1
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
