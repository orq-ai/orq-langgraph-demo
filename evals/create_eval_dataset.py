#!/usr/bin/env python3
"""
Script to upload the Hybrid Data Agent evaluation dataset to orq.ai.
"""

import json
import os
import sys

from dotenv import load_dotenv
from orq_ai_sdk import Orq

load_dotenv(override=True)

# Add src to path so we can import settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from core.settings import settings  # noqa: E402


def main():
    """Upload dataset to orq.ai."""

    print("Uploading Hybrid Data Agent Dataset to orq.ai")

    # Check API key
    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        print("ORQ_API_KEY not found. Set it first.")
        return 1

    # Load dataset
    filename = "evals/datasets/tool_calling_evals.jsonl"
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

    # Create dataset and upload datapoints
    with Orq(api_key=api_key) as client:
        dataset_name = "hybrid-data-agent-tool-calling-evals"

        print(f"Creating dataset: {dataset_name}")
        dataset = client.datasets.create(
            request={
                "display_name": dataset_name,
                "path": settings.ORQ_PROJECT_NAME,
            }
        )
        dataset_id = dataset.id

        # Build datapoints for bulk upload.
        # orq.ai inputs must be flat key-value pairs (no nested objects/arrays),
        # so we serialize any non-primitive values to JSON strings.
        items = []
        for ex in examples:
            flat_inputs = {
                k: json.dumps(v) if isinstance(v, (list, dict)) else v
                for k, v in ex["inputs"].items()
            }
            items.append(
                {
                    "inputs": flat_inputs,
                    "expected_output": json.dumps(ex["outputs"]),
                }
            )

        print(f"Uploading {len(items)} datapoints...")
        client.datasets.create_datapoint(
            dataset_id=dataset_id,
            request_body=items,
        )

        print(f"Success! Dataset ID: {dataset_id}")
        print(f"View at: https://my.orq.ai/datasets/{dataset_id}")

    return 0


if __name__ == "__main__":
    exit(main())
