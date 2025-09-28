#!/usr/bin/env python3
"""
Script to upload the Toyota assistant evaluation dataset to LangSmith.
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import LangSmith client
try:
    from langsmith import Client
except ImportError:
    print("LangSmith not installed. Run: pip install langsmith")
    sys.exit(1)


def main():
    """Upload dataset to LangSmith."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Upload Toyota assistant evaluation dataset to LangSmith"
    )
    parser.add_argument("dataset_file", help="Path to the JSONL dataset file to upload")
    parser.add_argument(
        "--dataset-name",
        help="Name for the dataset in LangSmith (default: auto-generated from filename)",
    )
    parser.add_argument(
        "--description", help="Description for the dataset (default: auto-generated from filename)"
    )

    args = parser.parse_args()

    print("Uploading Toyota Assistant Dataset to LangSmith")

    # Check API key
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("LANGCHAIN_API_KEY not found. Set it first.")
        return 1

    # Load dataset
    filename = args.dataset_file
    if not os.path.exists(filename):
        print(f"Dataset file not found: {filename}")
        return 1

    print(f"📂 Loading {filename}...")
    examples = []
    with open(filename, "r") as f:
        for line in f:
            if line.strip():
                examples.append(json.loads(line))

    print(f"Loaded {len(examples)} examples")

    # Generate dataset name from filename if not specified
    if args.dataset_name:
        dataset_name = args.dataset_name
    else:
        # Extract filename without extension and path
        base_name = os.path.splitext(os.path.basename(filename))[0]
        # Convert to a clean dataset name (replace underscores/hyphens with spaces, then title case)
        dataset_name = (
            base_name.replace("_", "-").replace("-", " ").title().replace(" ", "-").lower()
        )

    # Generate description if not specified
    if args.description:
        description = args.description
    else:
        # Create a description based on the filename
        base_name = os.path.splitext(os.path.basename(filename))[0]
        description = f"Toyota Assistant Evaluation Dataset - {base_name.replace('_', ' ').title()}"

    # Create dataset
    langsmith_client = Client()

    # Check if dataset already exists
    print(f"Checking if dataset '{dataset_name}' already exists...")
    existing_datasets = list(langsmith_client.list_datasets(dataset_name=dataset_name))

    if existing_datasets:
        dataset = existing_datasets[0]
        print(f"Dataset '{dataset_name}' already exists with ID: {dataset.id}")
        print(f"View at: https://smith.langchain.com/datasets/{dataset.id}")
        return 0

    print(f"Creating new dataset: {dataset_name}")
    dataset = langsmith_client.create_dataset(
        dataset_name=dataset_name,
        description=description,
    )
    print(f"Created new dataset with ID: {dataset.id}")

    # Upload examples
    print(f"Uploading {len(examples)} examples...")
    langsmith_client.create_examples(
        inputs=[ex["inputs"] for ex in examples],
        outputs=[ex["outputs"] for ex in examples],
        metadata=[ex["metadata"] for ex in examples],
        dataset_id=dataset.id,
    )

    print(f"Success! Dataset ID: {dataset.id}")
    print(f"Uploaded {len(examples)} examples to dataset '{dataset_name}'")
    print(f"View at: https://smith.langchain.com/datasets/{dataset.id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
