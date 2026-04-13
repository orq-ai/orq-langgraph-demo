#!/usr/bin/env python3
"""Run evaluatorq against the Hybrid Data Agent — single variant or A/B.

Single-variant run (default, uses the cached default system prompt):

    uv run python evals/run_evals.py

A/B run against the two prompt variants managed in orq.ai:

    uv run python evals/run_evals.py --variants A,B

The A/B run fetches each variant via `fetch_prompt_by_id()` and overrides
`Context(system_prompt=...)` per job, so editing a prompt in the Studio +
clicking Publish is enough to change what the next run evaluates. No code
change or redeploy required.

Requires in the environment:
    - ORQ_API_KEY
    - ORQ_PROJECT_NAME
    - ORQ_SYSTEM_PROMPT_ID            (for --variants A or default run)
    - ORQ_SYSTEM_PROMPT_ID_VARIANT_B  (for --variants A,B)

Run `make setup-workspace` to create both variants if they don't exist.
"""

import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

# Load env and set up OTEL tracing BEFORE importing langchain/evaluatorq
load_dotenv(override=True)

# Make src/ importable (the @job closure in _shared.py imports assistant.*)
_SRC_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../src"))
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from assistant.tracing import setup_tracing  # noqa: E402

setup_tracing()

from _shared import (  # noqa: E402
    load_datapoints_from_file,
    make_agent_job,
    tool_accuracy_scorer,
)
from evaluatorq import evaluatorq  # noqa: E402
from orq_scorers import (  # noqa: E402
    grounding_scorer,
    hallucination_scorer,
    source_citations_scorer,
)

from assistant.prompts import fetch_prompt_by_id  # noqa: E402
from core.settings import settings  # noqa: E402

# Known prompt variants. Add a new row and you can run `--variants A,B,C`.
VARIANT_PROMPT_IDS = {
    "A": settings.ORQ_SYSTEM_PROMPT_ID,
    "B": settings.ORQ_SYSTEM_PROMPT_ID_VARIANT_B,
}

EVALUATORS = [
    {"name": "tool-accuracy", "scorer": tool_accuracy_scorer},
    {"name": "source-citations", "scorer": source_citations_scorer},
    {"name": "response-grounding", "scorer": grounding_scorer},
    {"name": "hallucination-check", "scorer": hallucination_scorer},
]


async def run(variants: list[str]) -> None:
    print("Hybrid Data Agent — Evaluation Pipeline")
    print("=" * 50)
    print(f"Variants: {', '.join(variants)}")

    data = load_datapoints_from_file()
    total = len(data)
    print(f"Dataset:  {total} datapoints (local file)")

    if len(variants) == 1:
        # Single-variant run: use the default cached prompt (no round-trip
        # unless the agent's own `prompts.py` needs it).
        jobs = [make_agent_job(variants[0], system_prompt=None, total_rows=total)]
        name = "hybrid-data-agent-tool-calling-eval"
        description = None
    else:
        # A/B: fetch each variant's prompt so we can override Context per job.
        prompts: dict[str, str] = {}
        for v in variants:
            prompt_id = VARIANT_PROMPT_IDS[v]
            if not prompt_id:
                sys.exit(
                    f"Variant {v!r} requires a prompt ID in settings "
                    f"(check ORQ_SYSTEM_PROMPT_ID / ORQ_SYSTEM_PROMPT_ID_VARIANT_B)."
                )
            prompts[v] = fetch_prompt_by_id(prompt_id)
            print(f"  Variant {v}: {prompt_id} ({len(prompts[v])} chars)")

        jobs = [make_agent_job(v, system_prompt=prompts[v], total_rows=total) for v in variants]
        name = "hybrid-data-agent-prompt-ab"
        description = f"A/B: variants {', '.join(variants)}"

    print("\nStarting evaluation...\n")

    await evaluatorq(
        name,
        data=data,
        jobs=jobs,
        evaluators=EVALUATORS,
        path=settings.ORQ_PROJECT_NAME,
        description=description,
        # Don't abort on individual pass_=False rows. Local runs should
        # surface failures in the Studio, not fail the make target on
        # transient LLM-judge flakes. CI can re-enable this as a
        # regression gate.
        _exit_on_failure=False,
    )

    print("\nEvaluation complete.")
    print("Results available in orq.ai Studio: https://my.orq.ai/experiments")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--variants",
        default="A",
        help="Comma-separated prompt variants to run (default: 'A'). Use 'A,B' for A/B experiment.",
    )
    args = parser.parse_args()

    variants = [v.strip() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in variants if v not in VARIANT_PROMPT_IDS]
    if unknown:
        print(
            f"Unknown variants: {unknown}. Known: {sorted(VARIANT_PROMPT_IDS)}",
            file=sys.stderr,
        )
        return 1

    if not os.environ.get("ORQ_API_KEY"):
        print("Error: ORQ_API_KEY is not set. Add it to .env first.", file=sys.stderr)
        return 1

    try:
        asyncio.run(run(variants))
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
    sys.exit(main())
