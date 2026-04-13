#!/usr/bin/env python3
"""
Diagnostic script that checks every moving piece of the repo setup and
reports a clear ✓ / ✗ summary. Useful for first-run debugging and for
sanity-checking after pulling changes.

Usage:
    make doctor
    # or
    uv run python scripts/doctor.py
"""

import os
from pathlib import Path
import sqlite3
import sys
from typing import List, Optional, Tuple

from dotenv import load_dotenv
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))  # for `_term`

load_dotenv()

from _term import arrow, bold, fail, ok, section, warn  # noqa: E402

API_BASE = "https://api.orq.ai/v2"


class CheckFailed(Exception):
    """Raised when a check fails. The message is the remediation hint."""


def check_env_file() -> bool:
    """Check that .env exists and contains no malformed lines."""
    env_path = Path(".env")
    if not env_path.exists():
        fail(".env file not found", "run `cp .env.example .env` and fill in your keys")
        return False

    malformed_lines: List[Tuple[int, str]] = []
    with open(env_path) as f:
        for line_num, line in enumerate(f, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Valid dotenv line: KEY=VALUE or KEY="VALUE" or export KEY=VALUE
            if "=" not in stripped.split("#")[0]:
                malformed_lines.append((line_num, stripped[:60]))

    if malformed_lines:
        fail(f".env has {len(malformed_lines)} malformed line(s)")
        for line_num, content in malformed_lines[:3]:
            print(f"    line {line_num}: {content!r}")
        print(f"  {arrow()} remove or prefix with `#` to comment out")
        return False

    ok(".env parses cleanly")
    return True


def check_openai_key() -> bool:
    """Check OPENAI_API_KEY is set and can reach the API."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        fail("OPENAI_API_KEY not set", "add OPENAI_API_KEY=sk-... to .env")
        return False
    if not key.startswith("sk-"):
        warn("OPENAI_API_KEY format looks unusual (expected 'sk-...')")

    try:
        r = httpx.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        if r.status_code == 401:
            fail("OPENAI_API_KEY is set but rejected by api.openai.com")
            return False
        r.raise_for_status()
        ok("OPENAI_API_KEY set and valid")
        return True
    except Exception as e:
        fail(f"OPENAI_API_KEY check failed: {e}")
        return False


def check_orq_key() -> Optional[str]:
    """Check ORQ_API_KEY is set and can reach orq.ai. Returns the key on success."""
    key = os.environ.get("ORQ_API_KEY")
    if not key:
        fail("ORQ_API_KEY not set", "add ORQ_API_KEY=... to .env")
        return None

    try:
        r = httpx.get(
            f"{API_BASE}/projects",
            headers={"Authorization": f"Bearer {key}"},
            timeout=10.0,
        )
        if r.status_code == 401:
            fail("ORQ_API_KEY is set but rejected by api.orq.ai")
            return None
        r.raise_for_status()
        ok("ORQ_API_KEY set and valid")
        return key
    except Exception as e:
        fail(f"ORQ_API_KEY check failed: {e}")
        return None


def check_orq_project(api_key: str) -> bool:
    """Check ORQ_PROJECT_NAME exists on orq.ai."""
    name = os.environ.get("ORQ_PROJECT_NAME")
    if not name:
        fail("ORQ_PROJECT_NAME not set", "add ORQ_PROJECT_NAME=langgraph-demo to .env")
        return False

    try:
        r = httpx.get(
            f"{API_BASE}/projects",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        r.raise_for_status()
        projects = r.json()
        if any(p.get("name") == name or p.get("key") == name for p in projects):
            ok(f"Project '{name}' exists on orq.ai")
            return True
        fail(
            f"Project '{name}' not found in workspace",
            "run `make setup-workspace` to create it",
        )
        return False
    except Exception as e:
        fail(f"project check failed: {e}")
        return False


def check_knowledge_base(api_key: str) -> bool:
    """Check ORQ_KNOWLEDGE_BASE_ID exists and has completed chunks."""
    kb_id = os.environ.get("ORQ_KNOWLEDGE_BASE_ID")
    if not kb_id:
        fail(
            "ORQ_KNOWLEDGE_BASE_ID not set",
            "run `make setup-workspace`, then paste the printed ID into .env",
        )
        return False

    try:
        r = httpx.get(
            f"{API_BASE}/knowledge/{kb_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if r.status_code == 404:
            fail(
                f"Knowledge Base {kb_id} not found",
                "run `make setup-workspace` to create one and update .env",
            )
            return False
        r.raise_for_status()
    except Exception as e:
        fail(f"KB check failed: {e}")
        return False

    # List datasources and count chunks
    try:
        r = httpx.get(
            f"{API_BASE}/knowledge/{kb_id}/datasources?limit=50",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        r.raise_for_status()
        datasources = r.json().get("data", [])
    except Exception as e:
        fail(f"KB datasource check failed: {e}")
        return False

    if not datasources:
        fail(
            f"Knowledge Base {kb_id} has no datasources",
            "run `make ingest-kb` to upload the PDFs",
        )
        return False

    ok(f"Knowledge Base has {len(datasources)} datasource(s)")
    return True


def check_system_prompt(api_key: str) -> bool:
    """Check ORQ_SYSTEM_PROMPT_ID fetches successfully."""
    prompt_id = os.environ.get("ORQ_SYSTEM_PROMPT_ID")
    if not prompt_id:
        warn(
            "ORQ_SYSTEM_PROMPT_ID not set",
            "the app will use the local hardcoded fallback from src/assistant/prompts.py",
        )
        return True  # soft warning — local fallback is fine

    try:
        r = httpx.get(
            f"{API_BASE}/prompts/{prompt_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if r.status_code == 404:
            fail(
                f"System prompt {prompt_id} not found",
                "run `make setup-workspace` and paste the new ID into .env",
            )
            return False
        r.raise_for_status()
        body = r.json()
        messages = (body.get("prompt") or {}).get("messages") or []
        if not messages:
            fail(f"System prompt {prompt_id} has no messages")
            return False
        content = messages[0].get("content", "")
        ok(f"System prompt fetched ({len(content) if isinstance(content, str) else '?'} chars)")
        return True
    except Exception as e:
        fail(f"system prompt check failed: {e}")
        return False


def check_sqlite() -> bool:
    """Check the SQLite sales database exists and has rows."""
    # Read path from settings (deferred import so earlier failures don't block)
    try:
        from core.settings import settings  # noqa

        db_path = settings.DEFAULT_SQLITE_PATH
    except Exception:
        db_path = Path("delivery_orders.db")

    if not Path(db_path).exists():
        fail(
            f"SQLite database not found at {db_path}",
            "run `make ingest-sql` to create it",
        )
        return False

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5.0)
        cur = conn.execute("SELECT COUNT(*) FROM fact_orders")
        count = cur.fetchone()[0]
        conn.close()
    except Exception as e:
        fail(f"SQLite query failed: {e}")
        return False

    if count == 0:
        fail(
            "SQLite database is empty (fact_orders has 0 rows)",
            "run `make ingest-sql`",
        )
        return False

    ok(f"SQLite database has {count:,} rows in fact_orders")
    return True


def check_kb_search(api_key: str) -> bool:
    """Run a test search against the KB to verify retrieval works end-to-end."""
    kb_id = os.environ.get("ORQ_KNOWLEDGE_BASE_ID")
    if not kb_id:
        return True  # already reported by check_knowledge_base

    try:
        r = httpx.post(
            f"{API_BASE}/knowledge/{kb_id}/search",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "query": "Toyota warranty",
                "retrieval_config": {"type": "hybrid_search", "top_k": 3},
                "search_options": {"include_metadata": True, "include_scores": True},
            },
            timeout=15.0,
        )
        r.raise_for_status()
        matches = r.json().get("matches", [])
    except Exception as e:
        fail(f"KB search failed: {e}")
        return False

    if not matches:
        fail(
            "KB search returned 0 results for 'Toyota warranty'",
            "chunks may still be embedding — wait ~1 minute or re-run ingest-kb",
        )
        return False

    ok(f"KB search returned {len(matches)} result(s) for a test query")
    return True


def check_evaluatorq() -> bool:
    """Check if evaluatorq is installed (soft — only needed for eval pipeline)."""
    try:
        import evaluatorq  # noqa

        ok("evaluatorq installed (eval pipeline ready)")
        return True
    except ImportError:
        warn(
            "evaluatorq not installed",
            "run `uv sync --group eval` if you want to run the eval pipeline",
        )
        return True  # soft


def main() -> int:
    print(bold("Running diagnostic checks..."))

    passed = 0
    failed = 0

    def run(check_fn, *args):
        nonlocal passed, failed
        try:
            if check_fn(*args):
                passed += 1
            else:
                failed += 1
        except Exception as e:
            fail(f"{check_fn.__name__} raised {type(e).__name__}: {e}")
            failed += 1

    section("Environment")
    run(check_env_file)
    run(check_openai_key)
    api_key = check_orq_key()
    if api_key:
        passed += 1
    else:
        failed += 1

    if api_key:
        section("orq.ai workspace")
        run(check_orq_project, api_key)
        run(check_knowledge_base, api_key)
        run(check_system_prompt, api_key)
        run(check_kb_search, api_key)

    section("Local data")
    run(check_sqlite)

    section("Dev dependencies")
    run(check_evaluatorq)

    print()
    total = passed + failed
    if failed == 0:
        from _term import green  # noqa: PLC0415

        print(bold(green(f"All {total} checks passed ✓")))
        print("\nYou're ready to go. Try:")
        print("  make run          # start the Chainlit UI")
        print("  make evals-run    # run the evaluation pipeline")
        return 0
    else:
        from _term import red  # noqa: PLC0415

        print(bold(red(f"{failed} of {total} checks failed ✗")))
        print("\nFix the issues above and re-run `make doctor`.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
