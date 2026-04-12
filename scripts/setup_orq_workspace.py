#!/usr/bin/env python3
"""
Idempotent bootstrap for the orq.ai entities this project needs.

Creates (or reuses if they already exist by key/display_name):
    - Project         (name:         $ORQ_PROJECT_NAME)
    - Knowledge Base  (key:          hybrid-data-agent-kb)
    - System prompt   (display_name: hybrid-data-agent-system-prompt)
    - Eval dataset    (display_name: hybrid-data-agent-tool-calling-evals)

At the end, prints a ready-to-paste `.env` block with all IDs.

Usage:
    make setup-workspace
    # or
    uv run python scripts/setup_orq_workspace.py

Requires in the environment (via .env or shell):
    - ORQ_API_KEY
    - ORQ_PROJECT_NAME
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from assistant.prompts import SYSTEM_PROMPT  # noqa: E402
from core.settings import settings  # noqa: E402

load_dotenv()

API_BASE = "https://api.orq.ai/v2"

KB_KEY = "hybrid-data-agent-kb"
PROMPT_KEY = "hybrid-data-agent-system-prompt"
DATASET_KEY = "hybrid-data-agent-tool-calling-evals"
DATASET_JSONL = "evals/datasets/tool_calling_evals.jsonl"

EMBEDDING_MODEL = f"openai/{settings.EMBEDDING_MODEL}"
PROMPT_MODEL = settings.DEFAULT_MODEL


def _headers(api_key: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get(api_key: str, path: str) -> httpx.Response:
    return httpx.get(f"{API_BASE}{path}", headers=_headers(api_key), timeout=30.0)


def _post(api_key: str, path: str, payload: Any) -> httpx.Response:
    return httpx.post(
        f"{API_BASE}{path}",
        headers=_headers(api_key),
        json=payload,
        timeout=60.0,
    )


def _id(obj: Dict[str, Any]) -> Optional[str]:
    return obj.get("_id") or obj.get("id")


def _paginate(api_key: str, path: str, match_fn) -> Optional[Dict[str, Any]]:
    """Page through a list endpoint and return the first item where match_fn(item) is True.

    Uses cursor-based pagination via `starting_after`.
    """
    cursor: Optional[str] = None
    page = 0
    while True:
        page += 1
        query = "?limit=50"
        if cursor:
            query += f"&starting_after={cursor}"
        response = _get(api_key, f"{path}{query}")
        response.raise_for_status()
        body = response.json()
        items = body.get("data", []) or []
        if not items:
            return None
        for item in items:
            if match_fn(item):
                return item
        if not body.get("has_more"):
            return None
        cursor = _id(items[-1])
        if not cursor:
            return None
        if page > 50:  # safety cap: 50*50=2500 items
            return None


# ──────────────────────────────────────────────────────────────────────────────
# Project
# ──────────────────────────────────────────────────────────────────────────────


def setup_project(api_key: str, name: str) -> None:
    """Find or create the orq.ai project. Uses the project name as the identifier.

    The `/projects` endpoint returns a flat array (not paginated), so we don't
    reuse `_paginate` here.
    """
    print(f"\n[1/4] Project '{name}'")

    response = _get(api_key, "/projects")
    response.raise_for_status()
    projects = response.json() or []
    for project in projects:
        if project.get("name") == name or project.get("key") == name:
            print(f"  → reusing existing project: {project.get('_id')}")
            return

    # Create
    create_response = _post(api_key, "/projects", {"name": name})
    if create_response.status_code >= 400:
        raise RuntimeError(
            f"Failed to create project (status {create_response.status_code}): {create_response.text}"
        )
    body = create_response.json()
    print(f"  → created new project: {body.get('_id')}")


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Base
# ──────────────────────────────────────────────────────────────────────────────


def setup_knowledge_base(api_key: str, path: str) -> str:
    """Find or create the Knowledge Base. Returns its ID."""
    print(f"\n[2/4] Knowledge Base '{KB_KEY}'")

    existing = _paginate(api_key, "/knowledge", lambda kb: kb.get("key") == KB_KEY)
    if existing:
        kb_id = _id(existing)
        print(f"  → reusing existing KB: {kb_id}")
        return kb_id

    # Create new
    payload = {
        "key": KB_KEY,
        "embedding_model": EMBEDDING_MODEL,
        "path": path,
        "type": "internal",
    }
    response = _post(api_key, "/knowledge", payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Failed to create Knowledge Base: {response.text}")
    body = response.json()
    kb_id = _id(body)
    print(f"  → created new KB: {kb_id}")
    print(f"    Next step: run `make ingest-kb` to upload the PDFs.")
    return kb_id


# ──────────────────────────────────────────────────────────────────────────────
# System prompt
# ──────────────────────────────────────────────────────────────────────────────


def setup_system_prompt(api_key: str, path: str) -> str:
    """Find or create the system prompt. Returns its ID."""
    print(f"\n[3/4] System prompt '{PROMPT_KEY}'")

    existing = _paginate(
        api_key, "/prompts", lambda p: p.get("display_name") == PROMPT_KEY
    )
    if existing:
        prompt_id = _id(existing)
        print(f"  → reusing existing prompt: {prompt_id}")
        return prompt_id

    # Create new — convert Python `.format()` `{var}` placeholders to orq.ai `{{var}}`
    template = re.sub(r"(?<!\{)\{(\w+)\}(?!\})", r"{{\1}}", SYSTEM_PROMPT)

    payload = {
        "display_name": PROMPT_KEY,
        "path": path,
        "description": "Main system prompt for the Hybrid Data Agent (managed via orq.ai)",
        "prompt": {
            "model": PROMPT_MODEL,
            "model_type": "chat",
            "provider": "openai",
            "messages": [
                {"role": "system", "content": template},
            ],
        },
    }
    response = _post(api_key, "/prompts", payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Failed to create system prompt: {response.text}")
    body = response.json()
    prompt_id = _id(body)
    print(f"  → created new prompt: {prompt_id}")
    return prompt_id


# ──────────────────────────────────────────────────────────────────────────────
# Evaluation dataset
# ──────────────────────────────────────────────────────────────────────────────


def _load_datapoints() -> List[Dict[str, Any]]:
    """Load and flatten datapoints from the JSONL file for orq.ai upload."""
    jsonl_path = Path(DATASET_JSONL)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {DATASET_JSONL}")

    items = []
    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip():
                continue
            ex = json.loads(line)
            # orq.ai inputs must be flat primitives — serialize non-primitives to JSON strings
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
    return items


def setup_dataset(api_key: str, path: str) -> str:
    """Find or create the evaluation dataset. Returns its ID."""
    print(f"\n[4/4] Evaluation dataset '{DATASET_KEY}'")

    existing = _paginate(
        api_key, "/datasets", lambda d: d.get("display_name") == DATASET_KEY
    )
    if existing:
        dataset_id = _id(existing)
        count = (existing.get("metadata") or {}).get("datapoints_count", 0)
        print(f"  → reusing existing dataset: {dataset_id} ({count} datapoints)")
        return dataset_id

    # Create new dataset + upload datapoints
    payload = {"display_name": DATASET_KEY, "path": path}
    response = _post(api_key, "/datasets", payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Failed to create dataset: {response.text}")
    body = response.json()
    dataset_id = _id(body)
    print(f"  → created new dataset: {dataset_id}")

    items = _load_datapoints()
    print(f"  → uploading {len(items)} datapoints...")
    bulk_response = _post(
        api_key,
        f"/datasets/{dataset_id}/datapoints/bulk",
        {"items": items},
    )
    if bulk_response.status_code >= 400:
        raise RuntimeError(
            f"Failed to upload datapoints (status {bulk_response.status_code}): {bulk_response.text}"
        )
    print(f"  → uploaded {len(items)} datapoints")
    return dataset_id


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def main() -> int:
    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        print("Error: ORQ_API_KEY is not set. Add it to .env first.")
        return 1

    project_path = settings.ORQ_PROJECT_NAME
    print(f"Bootstrapping orq.ai workspace in project '{project_path}'")

    try:
        setup_project(api_key, project_path)
        kb_id = setup_knowledge_base(api_key, project_path)
        prompt_id = setup_system_prompt(api_key, project_path)
        dataset_id = setup_dataset(api_key, project_path)
    except Exception as e:
        print(f"\n❌ Bootstrap failed: {e}")
        return 1

    # Print ready-to-paste .env block.
    # Every non-env-var line is commented with `#` so the entire block below
    # the header can be pasted straight into .env without parse errors.
    print()
    print("=" * 70)
    print("✅ Workspace bootstrap complete")
    print("=" * 70)
    print()
    print("# Paste the block below into your .env file (safe to paste as-is).")
    print("# ───────────────────────────────────────────────────────────────")
    print(f'ORQ_KNOWLEDGE_BASE_ID="{kb_id}"')
    print(f'ORQ_SYSTEM_PROMPT_ID="{prompt_id}"')
    print(f"# Dataset ID (not read by the app, informational only):")
    print(f"# ORQ_DATASET_ID={dataset_id}")
    print("# ───────────────────────────────────────────────────────────────")
    print()
    print("Next steps:")
    print("  1. Paste the block above into .env")
    print("  2. Run `make ingest-data` to load SQLite sales + upload PDFs to the KB")
    print("  3. Run `make run` to start the app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
