#!/usr/bin/env python3
"""
Script to upload the Toyota assistant evaluation dataset to LangSmith.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

try:
    from langsmith import Client
except ImportError:
    print("LangSmith not installed. Run: pip install langsmith")
    exit(1)


def main():
    """Upload dataset to LangSmith."""

    print("Uploading Toyota Assistant Dataset to LangSmith")

    # Check API key
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("LANGCHAIN_API_KEY not found. Set it first.")
        return 1

    # Load dataset
    filename = "evals/datasets/toyota_assistant_tool_calling_evals.jsonl"
    if not os.path.exists(filename):
        print(f"Dataset file not found: {filename}")
        return 1

    print(f"Loading {filename}...")
    examples = []
    with open(filename, "r") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))

    print(f"Loaded {len(examples)} examples")

    # Create dataset
    client = Client()
    dataset_name = "toyota-assistant-tool-calling-evals"

    print(f"Creating dataset: {dataset_name}")
    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Toyota Assistant Tool Calling Evaluation Dataset - 15 test cases",
    )

    # Upload examples
    print(f"Uploading {len(examples)} examples...")
    client.create_examples(
        inputs=[ex["inputs"] for ex in examples],
        outputs=[ex["outputs"] for ex in examples],
        metadata=[ex["metadata"] for ex in examples],
        dataset_id=dataset.id,
    )

    print(f"Success! Dataset ID: {dataset.id}")
    print(f"View at: https://smith.langchain.com/datasets/{dataset.id}")

    return 0


if __name__ == "__main__":
    exit(main())
