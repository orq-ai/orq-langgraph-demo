#!/usr/bin/env python3
"""
Grow the eval dataset from orq.ai production traces.

The strongest reason to use orq.ai is the **production → eval loop**: every
trace you capture in the Studio is a potential eval datapoint. This script
closes that loop by reading exported traces, extracting the user question
and the tools the agent called, and appending them to
`evals/datasets/tool_calling_evals.jsonl` (de-duped by question).

## Usage

1. **Export traces from orq.ai**. Two options:

   a) Via the **Studio UI**:
      - Go to Traces → filter by project `langgraph-demo` and the
        `Hybrid Data Agent` entity
      - Select the traces you want → Export → save as JSON

   b) Via the **orq MCP server** (when available in your Claude Code session):
      - Run the `mcp__orq__list_traces` tool with your filters
      - Save the JSON output to a file

2. **Run this script in dry-run mode** first:

   ```
   uv run python scripts/grow_eval_dataset.py --from-file traces.json
   ```

   It will print how many new datapoints would be added, what categories
   they'd fall into, and which questions are duplicates (skipped).

3. **Append for real**:

   ```
   uv run python scripts/grow_eval_dataset.py --from-file traces.json --apply
   ```

4. **Run the eval pipeline against the grown dataset**:

   ```
   make evals-run
   ```

## Expected input shape

The script accepts either:

- A single trace object with `spans` or `events`
- A list of trace objects
- A `{"data": [...]}` wrapper (like `list_traces` response)

For each trace, it looks for:

- A user message (role=user in the input messages)
- Tool-call spans (span type matching `tool.*` or `span.tool_*`)

If both are present, the trace becomes a candidate datapoint with:

- `inputs.question` — the user message text
- `inputs.expected_tools` — list of tool names from the spans
- `inputs.category` — inferred from tool types: `sql_only`, `document_only`,
  or `mixed`

Candidates are deduped against existing datapoints by SHA-256 of the question.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

DATASET_PATH = Path("evals/datasets/tool_calling_evals.jsonl")

# Tool name classification. Adjust if the agent's tools change.
SQL_TOOLS = {
    "get_sales_by_model",
    "get_sales_by_country",
    "get_sales_by_region",
    "get_sales_trends",
    "get_top_performing_models",
    "get_powertrain_analysis",
    "get_top_countries_by_sales",
    "get_powertrain_sales_trends",
    "compare_models_by_brand",
}
DOC_TOOLS = {"search_documents", "list_available_documents", "search_in_document"}


def _hash_question(question: str) -> str:
    return hashlib.sha256(question.strip().lower().encode()).hexdigest()


def _load_existing_hashes() -> Set[str]:
    """Load hashes of questions already in the dataset."""
    if not DATASET_PATH.exists():
        return set()
    hashes = set()
    with open(DATASET_PATH) as f:
        for line in f:
            if not line.strip():
                continue
            try:
                ex = json.loads(line)
                question = ex.get("inputs", {}).get("question")
                if question:
                    hashes.add(_hash_question(question))
            except json.JSONDecodeError:
                continue
    return hashes


def _normalize_traces(raw: Any) -> List[Dict[str, Any]]:
    """Accept several input shapes and return a flat list of trace dicts."""
    if isinstance(raw, dict):
        if "data" in raw and isinstance(raw["data"], list):
            return raw["data"]
        if "traces" in raw and isinstance(raw["traces"], list):
            return raw["traces"]
        # Single trace
        if "spans" in raw or "events" in raw or "messages" in raw:
            return [raw]
    if isinstance(raw, list):
        return raw
    raise ValueError(
        f"Unexpected trace file shape: top-level type is {type(raw).__name__}"
    )


def _extract_user_question(trace: Dict[str, Any]) -> Optional[str]:
    """Pull the first user message out of a trace."""
    # Try common shapes
    messages = (
        trace.get("input", {}).get("messages")
        or trace.get("inputs", {}).get("messages")
        or trace.get("messages")
    )
    if isinstance(messages, list):
        for msg in messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get("role") or (msg.get("type") if msg.get("type") in ("user", "human") else None)
            if role in ("user", "human"):
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    # Multi-part content — join text parts
                    texts = [p.get("text", "") for p in content if isinstance(p, dict)]
                    joined = " ".join(t for t in texts if t)
                    if joined:
                        return joined
    # Fall back to first attribute named like "input" or "question"
    for key in ("input", "question", "query"):
        val = trace.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _extract_tool_names(trace: Dict[str, Any]) -> List[str]:
    """Collect all tool names called during a trace."""
    tools: List[str] = []
    spans = trace.get("spans") or trace.get("events") or []
    for span in spans:
        if not isinstance(span, dict):
            continue
        span_type = (span.get("type") or "").lower()
        name = span.get("name") or ""
        # Tool spans can appear as "tool", "span.tool_execution", etc.
        if "tool" in span_type and name and name not in tools:
            tools.append(name)
    return tools


def _classify(tool_names: List[str]) -> str:
    has_sql = any(t in SQL_TOOLS for t in tool_names)
    has_doc = any(t in DOC_TOOLS for t in tool_names)
    if has_sql and has_doc:
        return "mixed"
    if has_sql:
        return "sql_only"
    if has_doc:
        return "document_only"
    return "unknown"


def _trace_to_datapoint(trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    question = _extract_user_question(trace)
    if not question:
        return None
    tools = _extract_tool_names(trace)
    if not tools:
        return None  # skip traces where the agent didn't call any tools
    category = _classify(tools)
    if category == "unknown":
        return None  # skip unclassifiable traces
    return {
        "metadata": {
            "id": f"trace_{_hash_question(question)[:8]}",
            "category": category,
            "expected_tools": tools,
            "source": "production-trace",
        },
        "inputs": {
            "category": category,
            "question": question,
            "expected_tools": tools,
        },
        "outputs": {
            "tools_called": tools,
            "execution_status": "success",
        },
    }


def _collect_new_datapoints(
    traces: List[Dict[str, Any]], existing: Set[str]
) -> Tuple[List[Dict[str, Any]], int, int]:
    """Return (new_datapoints, skipped_dupes, skipped_unusable)."""
    new_datapoints: List[Dict[str, Any]] = []
    skipped_dupes = 0
    skipped_unusable = 0
    seen_in_batch: Set[str] = set()

    for trace in traces:
        dp = _trace_to_datapoint(trace)
        if dp is None:
            skipped_unusable += 1
            continue
        question_hash = _hash_question(dp["inputs"]["question"])
        if question_hash in existing or question_hash in seen_in_batch:
            skipped_dupes += 1
            continue
        seen_in_batch.add(question_hash)
        new_datapoints.append(dp)

    return new_datapoints, skipped_dupes, skipped_unusable


def _append_to_jsonl(datapoints: List[Dict[str, Any]]) -> None:
    with open(DATASET_PATH, "a") as f:
        for dp in datapoints:
            f.write(json.dumps(dp) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Grow the eval dataset from orq.ai production traces",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--from-file",
        required=True,
        help="Path to a JSON file containing exported traces",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually append to the dataset (default is dry-run)",
    )
    args = parser.parse_args()

    input_path = Path(args.from_file)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        return 1

    try:
        raw = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Could not parse {input_path}: {e}")
        return 1

    traces = _normalize_traces(raw)
    print(f"Loaded {len(traces)} trace(s) from {input_path}")

    existing = _load_existing_hashes()
    print(f"Existing dataset: {len(existing)} datapoint(s) in {DATASET_PATH}")

    new_datapoints, skipped_dupes, skipped_unusable = _collect_new_datapoints(
        traces, existing
    )

    print()
    print(f"New datapoints:      {len(new_datapoints)}")
    print(f"Skipped (duplicate): {skipped_dupes}")
    print(f"Skipped (unusable):  {skipped_unusable}")

    if new_datapoints:
        print("\nCategory breakdown:")
        counts: Dict[str, int] = {}
        for dp in new_datapoints:
            cat = dp["inputs"]["category"]
            counts[cat] = counts.get(cat, 0) + 1
        for cat, n in sorted(counts.items()):
            print(f"  {cat:20s} {n}")

        print("\nSample new questions:")
        for dp in new_datapoints[:5]:
            q = dp["inputs"]["question"][:80]
            tools = ", ".join(dp["inputs"]["expected_tools"])
            print(f"  • {q}")
            print(f"    tools: {tools}")

    if args.apply:
        if not new_datapoints:
            print("\nNothing to append.")
            return 0
        _append_to_jsonl(new_datapoints)
        print(f"\n✅ Appended {len(new_datapoints)} datapoint(s) to {DATASET_PATH}")
        print("Re-run `make evals-run` to see the impact on tool-accuracy scores.")
    else:
        print("\n(dry run — re-run with --apply to append)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
