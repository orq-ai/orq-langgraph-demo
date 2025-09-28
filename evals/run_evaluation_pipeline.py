#!/usr/bin/env python3
"""
Run evaluation pipeline against the Toyota assistant using LangSmith.

This script runs your Toyota assistant against the LangSmith dataset
and tracks evaluation metrics.

Usage:
    python run_langsmith_evaluation.py [dataset_name]
    python run_langsmith_evaluation.py --list-datasets
    python run_langsmith_evaluation.py --help
"""

import argparse
import asyncio
from datetime import datetime
import os
import sys
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

# Add the project root to Python path so we can import the assistant module
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
sys.path.insert(0, project_root)


try:
    from langsmith import Client
    from langsmith.evaluation import aevaluate

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("LangSmith not installed. Install with: uv add langsmith")

# load environment variables
load_dotenv()


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
            # This is a ToolMessage (response from a tool)
            tool_name = message.name
            if tool_name and tool_name not in tools_called:
                tools_called.append(tool_name)

    return tools_called


async def toyota_assistant_runner(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the Toyota assistant with a question and return the result.

    This function should be replaced with your actual assistant integration.
    """
    question = inputs["question"]
    expected_tools = inputs.get("expected_tools", [])

    print(f"Question: {question}")
    print(f"Expected tools: {expected_tools}")

    # Run our assistant graph
    from assistant.context import Context
    from assistant.graph import graph

    # Create context with default settings
    context = Context()

    # Invoke the graph with proper context
    result = await graph.ainvoke({"messages": [HumanMessage(content=question)]}, context=context)
    response = result["messages"][-1].content
    tools_called = extract_tools_from_messages(result["messages"])

    return {"response": response, "tools_called": tools_called}


def tool_accuracy_evaluator(run, example):
    """Evaluate tool selection accuracy."""
    expected_tools = set(example.inputs.get("expected_tools", []))
    actual_tools = set(run.outputs.get("tools_called", []))

    # Check if all expected tools are present (allowing for additional tools)
    expected_present = expected_tools.issubset(actual_tools)

    if expected_tools == actual_tools:
        return {"key": "tool_accuracy", "score": 1.0, "reason": "Perfect tool match"}
    elif expected_present:
        # All expected tools present, additional tools are okay
        return {
            "key": "tool_accuracy",
            "score": 1.0,
            "reason": f"All {len(expected_tools)} expected tools present (with {len(actual_tools) - len(expected_tools)} additional)",
        }
    elif expected_tools.intersection(actual_tools):
        # Some expected tools missing
        overlap = len(expected_tools.intersection(actual_tools))
        score = overlap / len(expected_tools)
        return {
            "key": "tool_accuracy",
            "score": score,
            "reason": f"Partial match: {overlap}/{len(expected_tools)} expected tools present",
        }
    else:
        return {"key": "tool_accuracy", "score": 0.0, "reason": "No expected tools present"}


def category_accuracy_evaluator(run, example):
    """Evaluate accuracy by question category."""
    category = example.inputs.get("category", "unknown")
    expected_tools = set(example.inputs.get("expected_tools", []))
    actual_tools = set(run.outputs.get("tools_called", []))

    # Check if all expected tools are present (allowing for additional tools)
    expected_present = expected_tools.issubset(actual_tools)

    # Calculate partial score based on how many expected tools were called
    if expected_tools:
        overlap = len(expected_tools.intersection(actual_tools))
        partial_score = overlap / len(expected_tools)
    else:
        partial_score = 1.0

    # Use strict matching for exact score, partial for more lenient scoring
    score = 1.0 if expected_present else partial_score

    return {
        "key": f"category_accuracy_{category}",
        "score": score,
        "category": category,
        "expected_tools": list(expected_tools),
        "actual_tools": list(actual_tools),
        "expected_present": expected_present,
    }


async def run_evaluation(dataset_name: str):
    """Run evaluation against the LangSmith dataset."""

    if not LANGSMITH_AVAILABLE:
        raise ImportError("LangSmith not available. Please install: pip install langsmith")

    client = Client()

    # Get dataset info
    try:
        dataset = client.read_dataset(dataset_name=dataset_name)
        example_count = getattr(dataset, "example_count", "Unknown")
        print(f"Dataset: {dataset_name}")
        print(f"Examples: {example_count}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"Could not fetch dataset info: {e}")
        print(f"Dataset: {dataset_name}")

    # Define evaluators
    evaluators = [
        tool_accuracy_evaluator,
        category_accuracy_evaluator,
        # response_quality_evaluator, TODO: properly support answer quality evaluation
    ]

    print(f"Active Evaluators: {len(evaluators)} ({', '.join(str(e) for e in evaluators)})")

    # Run the evaluation
    print("Starting evaluation...")
    start_time = datetime.now()

    results = await aevaluate(
        toyota_assistant_runner,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix="toyota-assistant-tool-calling-eval",
        metadata={
            "evaluation_type": "tool_selection_and_quality",
            "timestamp": start_time.isoformat(),
            "description": "Evaluation of Toyota assistant tool selection and response quality",
            "dataset_name": dataset_name,
        },
    )

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print(f"Evaluation completed in {duration:.1f} seconds")

    return results


def list_available_datasets() -> List[Dict[str, Any]]:
    """List all available LangSmith datasets."""
    if not LANGSMITH_AVAILABLE:
        raise ImportError("LangSmith not available. Please install: pip install langsmith")

    client = Client()
    datasets = list(client.list_datasets())

    return [
        {
            "name": dataset.name,
            "id": str(dataset.id),
            "description": getattr(dataset, "description", "No description"),
            "created_at": getattr(dataset, "created_at", "Unknown"),
            "example_count": getattr(dataset, "example_count", 0),
        }
        for dataset in datasets
    ]


def setup_environment():
    """Setup LangSmith environment."""

    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("LANGCHAIN_API_KEY not found in environment variables")
        return False

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_PROJECT", "Toyota-Assistant-Evaluation")

    return True


def print_datasets():
    """Print available datasets in a formatted table."""
    try:
        datasets = list_available_datasets()

        if not datasets:
            print("No datasets found in LangSmith")
            return

        print("Available LangSmith Datasets:")
        print("=" * 80)
        print(f"{'Name':<40} {'Examples':<10} {'Created':<20} {'Description'}")
        print("-" * 80)

        for dataset in datasets:
            name = dataset["name"][:39] + "..." if len(dataset["name"]) > 40 else dataset["name"]
            examples = str(dataset["example_count"])
            created = (
                str(dataset["created_at"])[:19] if dataset["created_at"] != "Unknown" else "Unknown"
            )
            description = (
                dataset["description"][:30] + "..."
                if len(dataset["description"]) > 30
                else dataset["description"]
            )

            print(f"{name:<40} {examples:<10} {created:<20} {description}")

        print("=" * 80)

    except Exception as e:
        print(f"Failed to list datasets: {e}")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run evaluations against the Toyota assistant using LangSmith",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python run_langsmith_evaluation.py
  python run_langsmith_evaluation.py my-dataset-name
  python run_langsmith_evaluation.py --list-datasets
        """,
    )

    parser.add_argument(
        "dataset_name", nargs="?", help="Name of the LangSmith dataset to evaluate against"
    )

    parser.add_argument(
        "--list-datasets", action="store_true", help="List all available datasets and exit"
    )

    return parser.parse_args()


async def main():
    """Main evaluation function."""

    print("Toyota Assistant Evaluation Pipeline")
    print("====================================")

    try:
        # Parse arguments
        args = parse_arguments()

        # Handle list datasets command
        if args.list_datasets:
            print_datasets()
            return 0

        # Setup environment
        if not setup_environment():
            print("Please configure LangSmith environment variables")
            print("   Set LANGCHAIN_API_KEY in your .env file or environment")
            return 1

        if not LANGSMITH_AVAILABLE:
            print("LangSmith not installed. Run: pip install langsmith")
            return 1

        # Determine dataset name
        if args.dataset_name:
            dataset_name = args.dataset_name
        else:
            # Default fallback
            dataset_name = "toyota-assistant-tool-calling-evaluation"
            print(f"Using default dataset: {dataset_name}")
            print("   Use --list-datasets to see all available datasets")
            print(
                "   Specify dataset name as argument: python run_langsmith_evaluation.py <dataset_name>"
            )

        print(f"\nDataset: {dataset_name}")
        print("Project: Toyota-Assistant-Evaluation")
        print("LangSmith UI: https://smith.langchain.com/")

        # Run evaluation
        print("\nRunning evaluation...")
        print("   This may take a few minutes depending on dataset size...")

        await run_evaluation(dataset_name)

        print("\nEvaluation completed successfully!")
        print("Results available in LangSmith UI")
        print("View at: https://smith.langchain.com/")
        print("Check the 'Toyota-Assistant-Evaluation' project for detailed metrics")

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
