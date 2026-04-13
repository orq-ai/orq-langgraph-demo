# Plan: Repository improvements — turn orq-langgraph-reference into a first-class educational showcase

## Context

The repo works end-to-end and already integrates all the core orq.ai features (Router, KB, Prompts, Traces, evaluatorq, Datasets). However, it reads like "a Toyota RAG agent that happens to use orq.ai" rather than "the canonical way to build LangGraph agents on orq.ai." The goal of this plan is to systematically address that gap across 10 improvements, grouped into 4 phases by dependency order.

**The improvements target three audiences:**
1. **First-time visitors** — need to understand what they'll learn in <30 seconds
2. **Engineers evaluating the platform** — need runnable, credible comparisons and end-to-end demos
3. **Teams adopting orq.ai** — need production patterns (CI, guardrails, eval-driven dev loop)

Each phase is independently shippable so progress can be made incrementally and the repo becomes more useful with every merged phase.

**Critical files already in place (to be reused):**
- `src/assistant/graph.py` — LangGraph workflow (nodes, routing, tool loop)
- `src/assistant/prompts.py` — `get_system_prompt()` fetcher with local fallback (Phase A of prompts plan)
- `src/assistant/tracing.py` — OTEL tracing with `atexit` flush
- `src/assistant/utils.py:93` — `load_chat_model()` (needs the ChatOpenAI router fix)
- `scripts/setup_orq_workspace.py` — idempotent bootstrap (reuse for `make doctor`)
- `evals/run_evaluation_pipeline.py` — evaluatorq jobs + scorers (reuse for prompt A/B)
- `evals/datasets/tool_calling_evals.jsonl` — 15 test cases (reuse for prompt A/B + trace-driven growth)

---

## Phase 1 — Quick wins (foundation, ~1 day total)

No dependencies. Can be executed in any order, or in parallel.

### 1.1 — Reframe README around learning outcomes

**Why:** The opening currently describes the Toyota sample data, not the orq.ai capabilities. First-time visitors should see a "What you'll learn" table within the first screen.

**Files to modify:**
- `README.md` — replace/augment the intro section

**Changes:**
- Move the "What you'll learn" section to just below the title, before "What it does"
- Add a table: `orq.ai feature → problem it solves → code pointer`
- Reorder: put the **Observability** section higher (it's the most visual and compelling proof)
- Add a single-sentence tagline under the title: "A runnable reference implementation showing how to build, observe, and evaluate LangGraph agents on orq.ai."

**Verification:**
- Open README in a Markdown preview, verify the table renders correctly
- Check that links in the table resolve to real file paths/line numbers
- Ask a colleague to skim the top 30 lines and describe what the repo teaches

---

### 1.2 — Add `make doctor` diagnostics command

**Why:** First-run friction is the #1 abandonment cause for reference repos. A diagnostic command that checks every moving piece eliminates the "it doesn't work, what now?" cycle.

**Files to create:**
- `scripts/doctor.py` — idempotent diagnostic script

**Files to modify:**
- `Makefile` — add `doctor` target

**Checks to run** (in order, with clear ✓/✗ output):
1. `.env` file exists and parses cleanly (no malformed lines like the one we hit)
2. `OPENAI_API_KEY` is set (test with a cheap `/v1/models` call)
3. `ORQ_API_KEY` is set (test with a `/v2/projects` call)
4. `ORQ_PROJECT_NAME` exists on orq.ai
5. `ORQ_KNOWLEDGE_BASE_ID` exists and has `datapoints_count > 0`
6. KB chunks are all `status: completed` (not stuck in `pending`)
7. `ORQ_SYSTEM_PROMPT_ID` exists and fetches successfully
8. SQLite database exists at `DEFAULT_SQLITE_PATH` and has rows in `fact_sales`
9. A test search query returns at least one match
10. evaluatorq is installed (warn, don't fail, if eval group not synced)

**Output format:**
```
✓ .env parses cleanly
✓ OPENAI_API_KEY set (gpt-4o accessible)
✓ ORQ_API_KEY set (workspace: langgraph-demo)
✓ Knowledge Base 01KP1C... has 3349 chunks (all completed)
✓ System prompt fetched (3414 chars)
✗ .env line 11 is malformed: "Dataset ID (optional..."
   Fix: remove or comment that line with `#`
```

**Verification:**
- Run `make doctor` on a clean repo — every check should fail with a clear remediation
- Run after `make setup-workspace` + paste IDs — every check should pass
- Run with a deliberately malformed `.env` — should report the exact line

---

### 1.3 — Add TROUBLESHOOTING.md with real pitfalls

**Why:** We hit real SDK/API mismatches during this migration. Documenting them saves future readers hours and also implicitly tells them "this repo was built by someone who used the platform for real."

**Files to create:**
- `TROUBLESHOOTING.md` — categorized list of real issues and fixes

**Sections:**
- **SDK vs API drift** — when `prompt_config` is expected but API returns `prompt`; when `CreateKnowledgeRequestBody` is missing `type: "internal"`; when typed chunk metadata strips custom fields. Show the symptom, the root cause, and the workaround (raw HTTP).
- **OTEL tracing** — `BatchSpanProcessor` must flush on exit for short-lived scripts; the `LANGSMITH_OTEL_*` env vars are required for LangGraph; import order matters (setup tracing before langchain/evaluatorq).
- **Knowledge Base** — chunk upload limit is 100 per request; embedding is async so searches return 0 results for ~1 minute after upload; `search_options: {include_metadata: true, include_scores: true}` is required to get scores back.
- **Datapoints/Datasets** — `inputs` must be flat primitives; arrays/objects must be serialized to JSON strings; list endpoints are paginated (we need `_paginate` helper).
- **Guardrail / `LANGSMITH_OTEL_ENABLED`** — the name is misleading, it's for LangGraph OTEL export (not LangSmith submission). We set it but never talk to LangSmith.

**Verification:**
- Each entry includes a code snippet or file reference from our actual codebase showing the fix
- Link from README's Troubleshooting section to this file

---

### 1.4 — Fix `load_chat_model` to work with any router model (prereq for Phase 2.2)

**Why:** Today `src/assistant/utils.py:102` uses `init_chat_model(model, model_provider=provider, ...)`. For `openai/*` models this instantiates `ChatOpenAI` with our router `base_url` and works. For `anthropic/claude-...` it tries to instantiate `ChatAnthropic` which ignores `base_url`, so the router is bypassed. This blocks the model-swap demo in Phase 2.2.

**Files to modify:**
- `src/assistant/utils.py:93-110` — `load_chat_model()`

**Change:**
```python
from langchain_openai import ChatOpenAI

def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model via the orq.ai AI Router.

    The router is OpenAI-protocol-compatible regardless of the underlying
    provider, so we always use ChatOpenAI and pass the fully-specified
    model name straight through (e.g. "openai/gpt-4.1-mini",
    "anthropic/claude-sonnet-4-5", "groq/llama-3.3-70b-versatile").
    """
    return ChatOpenAI(
        model=fully_specified_name,
        api_key=os.getenv("ORQ_API_KEY"),
        base_url="https://api.orq.ai/v2/router",
    )
```

**Verification:**
- With `DEFAULT_MODEL="openai/gpt-4.1-mini"` — app runs as before (trace span shows `openai/gpt-4.1-mini`)
- With `DEFAULT_MODEL="anthropic/claude-sonnet-4-5"` — app runs, trace span shows Claude
- With `DEFAULT_MODEL="groq/llama-3.3-70b-versatile"` — app runs, trace span shows Groq
- `make evals-run` still passes (regression check)

---

## Phase 2 — Core showcases (the educational payoff, ~2 days)

Depends on Phase 1 completing cleanly. This is the phase where the repo becomes uniquely valuable.

### 2.1 — Prompt A/B experiment (Phase B of the prompts plan)

**Why:** We already migrated `SYSTEM_PROMPT` to orq.ai. The payoff of that work is A/B testing two versions against the eval dataset and choosing the winner based on scorers. This closes the full platform loop: **prompt mgmt → dataset → experiment → scoring → decision**. Nothing else in the repo showcases orq.ai as compellingly.

**Files to create:**
- `evals/run_prompt_experiment.py` — runs the same eval job twice, each with a different prompt version

**Files to modify:**
- `Makefile` — add `evals-compare-prompts` target
- `scripts/setup_orq_workspace.py` — optionally create a second prompt variant (`hybrid-data-agent-system-prompt-variant-b`) if missing
- `README.md` — new section "Prompt A/B testing" showing the workflow and results
- `plans/manage-prompts-on-orq.md` — mark Phase B as complete

**Design:**
1. In `scripts/setup_orq_workspace.py`, add a second prompt creation (variant B = a more concise version of the main prompt — we'll define the content in a file `prompts/variant-b.txt` or inline)
2. Store both prompt IDs in settings: `ORQ_SYSTEM_PROMPT_ID` (default/variant-a) and `ORQ_SYSTEM_PROMPT_ID_VARIANT_B`
3. `evals/run_prompt_experiment.py`:
   - Loads the dataset from the JSONL file (or orq.ai dataset via `DatasetIdInput`)
   - Defines two jobs: `hybrid-data-agent-v-a` and `hybrid-data-agent-v-b`, each fetching its respective prompt ID
   - Runs evaluatorq with both jobs + existing scorers
   - Prints a side-by-side comparison table: pass rate per scorer per variant
4. Results sync to orq.ai Studio under `langgraph-demo` project → Experiments

**Verification:**
- `make evals-compare-prompts` runs both variants, prints a comparison
- Results appear in orq.ai Studio with both variants visible
- The experiment URL is emitted at the end of the run

---

### 2.2 — Model swap demo

**Why:** "Swap providers in one line" is the AI Router's main selling point but the README doesn't show it concretely. After Phase 1.4, the fix is in place — we just need to demonstrate it.

**Files to modify:**
- `README.md` — new "Swap models via the AI Router" section
- `.env.example` — add commented examples of non-OpenAI models

**Content:**
- Three one-line `.env` changes (openai/gpt-4.1-mini → anthropic/claude-sonnet-4-5 → groq/llama-3.3-70b-versatile)
- A screenshot or trace snippet showing the same query answered by each model with different latencies/costs
- A brief note: "no code changes required — the router handles provider dispatch"

**Verification:**
- Manually swap each model in `.env` and run a query
- Confirm orq.ai traces show the correct model name per run
- Confirm the screenshots/data in the README are real (not mocked)

---

### 2.3 — Animated "tour" GIF

**Why:** A single 15-second loop showing the platform value is worth 500 words in the README.

**Files to create:**
- `media/tour.gif` — a screen recording

**Recording storyboard:**
1. Terminal: `make run` → Chainlit opens
2. User asks "What's the Toyota warranty for Europe?"
3. Agent streams response
4. Switch to browser: orq.ai Studio → Traces tab
5. Click the just-created trace → tree view expands (guard_input → analyze_and_route_query → call_model → tools → call_model)
6. Click a ChatOpenAI span → right panel shows token counts + cost
7. Switch to Experiments tab → most recent experiment → hover a PASS row

**Files to modify:**
- `README.md` — add the GIF right after the title, before "What you'll learn"

**Verification:**
- GIF loops smoothly (<20 seconds, <5MB)
- README renders the GIF correctly
- The story is understandable without sound or captions

---

## Phase 3 — Production polish (proves it's not a toy, ~1.5 days)

### 3.1 — Real CI/CD via GitHub Actions

**Why:** The README claims GitHub Actions CI/CD but there's no workflow file. Adding real CI that runs `make evals-run` on every PR proves this isn't just a demo — it's testable.

**Files to create:**
- `.github/workflows/test.yml` — unit tests + lint on every PR (Python 3.11 + 3.12 matrix)
- `.github/workflows/evals.yml` — runs `make evals-run` on PRs that touch `src/assistant/` or `evals/`, fails the PR on regression
- `.github/workflows/nightly.yml` — runs the full prompt A/B experiment nightly, posts results as a comment on the main branch

**Secrets required** (documented in README):
- `OPENAI_API_KEY`
- `ORQ_API_KEY`
- `ORQ_PROJECT_NAME`
- `ORQ_KNOWLEDGE_BASE_ID`
- `ORQ_SYSTEM_PROMPT_ID`

**Design notes:**
- The eval workflow uses evaluatorq's built-in `pass_=False` → exit code 1 mechanism for regression detection
- The nightly workflow checks out main, runs the full experiment, uses the orq.ai Studio URL in the comment
- Cache the uv venv between runs

**Verification:**
- Open a PR that deliberately breaks a tool → eval workflow fails, clear error in logs
- Open a PR with no src changes → eval workflow is skipped
- After one nightly run → PR comment appears with experiment URL

---

### 3.2 — Replace OpenAI moderation with an orq.ai guardrail evaluator

**Why:** Today `src/assistant/guardrails.py` (likely) uses OpenAI's moderation API for the input safety check. Replacing it with an orq.ai LLM evaluator configured as a guardrail:
1. Removes an external dependency
2. Makes the safety policy tunable in the Studio without code changes
3. Automatically shows failing traces in orq.ai (vs. being invisible today)
4. Teaches the reader a second orq.ai feature (guardrails on top of evaluators)

**Files to inspect first:**
- `src/assistant/guardrails.py` — see how the moderation check is wired today
- `src/assistant/graph.py` — find the `guard_input` node

**Files to modify:**
- `src/assistant/guardrails.py` — replace the OpenAI moderation call with an orq.ai evaluator `.invoke()`
- `scripts/setup_orq_workspace.py` — add a 5th bootstrap step: create the safety LLM evaluator
- `README.md` — mention the swap in the "How it works" section
- `ARCHITECTURE.md` — update the Security Architecture table

**Evaluator design:**
- Type: `llm_eval`
- Output type: `boolean` (True = safe, False = unsafe)
- Prompt: short classification prompt that returns `True` for benign queries and `False` for harmful ones
- Configure as a guardrail with `passes on True`

**Verification:**
- "What's the warranty on RAV4?" → evaluator returns True → agent proceeds
- "How do I make a bomb?" → evaluator returns False → agent blocks with refusal
- Both invocations appear as spans in the trace tree under `guard_input`
- `make setup-workspace` is idempotent on the new evaluator

---

## Phase 4 — Advanced educational content (highest teaching value, ~2 days)

### 4.1 — Side-by-side: LangGraph agent vs orq.ai managed Agent

**Why:** Every engineer evaluating the orq.ai platform asks "should I build my agent in code or in the Studio?" Nobody has written a credible, code-first comparison. This repo is in the perfect position to be that reference.

**Files to create:**
- `docs/comparing-approaches.md` — the comparison doc
- `src/orq_agent.py` — a minimal alternative entry point that invokes a managed orq.ai Agent instead of the LangGraph graph
- `src/chainlit_app_orq.py` — an alternate Chainlit entry point that uses `orq_agent.py`

**Files to modify:**
- `Makefile` — add `run-orq-agent` target (vs existing `run`)
- `scripts/setup_orq_workspace.py` — add a 6th bootstrap step: create the orq.ai Agent with the same tools + KB + prompt
- `README.md` — add a section linking to the comparison doc

**Comparison doc structure:**

| Dimension | LangGraph agent (src/assistant/graph.py) | orq.ai managed Agent |
|---|---|---|
| **Where the logic lives** | Python code in the repo | orq.ai Studio (JSON config) |
| **Observability** | Via OTEL → orq.ai Traces | Native, auto-attached |
| **Iteration loop** | Code push → CI → deploy | Publish in Studio → takes effect immediately |
| **Versioning** | Git commits | Studio version history + environment tags |
| **Tool definitions** | Python functions with `@tool` | Registered in Studio, optionally Python-backed |
| **Routing / conditional edges** | Explicit `StateGraph` nodes | Implicit — the Agent LLM decides |
| **When to pick which** | Complex custom routing, safety, multi-agent coordination | Simpler agents, product teams iterate, A/B testing Agents themselves |

**Verification:**
- `make run` → LangGraph flow
- `make run-orq-agent` → managed Agent flow
- Both answer "What's the Toyota warranty for Europe?" with similar quality
- Both produce traces visible in orq.ai Studio
- The comparison doc references specific line numbers in both entry points

---

### 4.2 — Trace-driven dataset growth ~~(dropped)~~

**Status: removed.** Attempted via a `scripts/grow_eval_dataset.py` + `make evals-grow-from-traces` target. The public orq.ai REST API does not expose a trace-listing endpoint (`/v2/traces` returns 404 on both `api.orq.ai` and `my.orq.ai`), and the MCP tool `mcp__orq__list_traces` that works in Claude Code talks to a JSON-RPC transport that a standalone Make target can't reach. Without a clean one-command flow this feature reduces to a clunky manual export dance that nobody would actually run — so we deleted the script, doc, and make target rather than ship a two-step stub. Revisit if/when `/v2/traces` is exposed publicly.

---

## Execution order & timeline

| Phase | Items | Dependency | Est. effort |
|---|---|---|---|
| Phase 1 | 1.1, 1.2, 1.3, 1.4 | None (parallelizable) | ~1 day |
| Phase 2 | 2.1, 2.2, 2.3 | 1.4 is a prereq for 2.2 | ~2 days |
| Phase 3 | 3.1, 3.2 | Phase 2 complete (for evals CI) | ~1.5 days |
| Phase 4 | 4.1, 4.2 | Phase 1 & 2 complete | ~2 days |
| **Total** | **10 items** | | **~6.5 days** |

Each phase ends in a shippable commit. Phase 1 alone is already a meaningful improvement.

---

## Files overview (what gets created/modified across all phases)

**New files:**
- `scripts/doctor.py` (1.2)
- `TROUBLESHOOTING.md` (1.3)
- `evals/run_prompt_experiment.py` (2.1)
- `media/tour.gif` (2.3)
- `.github/workflows/test.yml` (3.1)
- `.github/workflows/evals.yml` (3.1)
- `.github/workflows/nightly.yml` (3.1)
- `docs/comparing-approaches.md` (4.1)
- `src/orq_agent.py` (4.1)
- `src/chainlit_app_orq.py` (4.1)

**Modified files (touched by multiple phases):**
- `README.md` — 1.1, 2.2, 2.3, 3.2, 4.1
- `Makefile` — 1.2, 2.1, 3.2, 4.1
- `scripts/setup_orq_workspace.py` — 2.1, 3.2, 4.1
- `src/assistant/utils.py` — 1.4
- `src/assistant/guardrails.py` — 3.2
- `ARCHITECTURE.md` — 3.2, 4.1
- `EVALS.md` — 2.1
- `.env.example` — 2.2
- `plans/manage-prompts-on-orq.md` — 2.1 (mark Phase B complete)

---

## Verification at the end of all phases

After everything is merged, the repo should pass this smell test:

1. **A newcomer lands on the README** — within 30 seconds they understand: this is a LangGraph + orq.ai reference. They see the feature table, the tour GIF, and the KB/traces screenshots.
2. **They clone it** — `make setup-workspace && make ingest-data && make doctor && make run` works on the first try. Any failure has a clear remediation from `make doctor`.
3. **They try the fancy stuff** — `make evals-compare-prompts` shows two prompt variants side by side, `make run-orq-agent` shows the alternative approach.
4. **They open a PR** — CI runs lint, tests, and evals. If tool-accuracy drops, the PR turns red automatically.
5. **They swap models** — change `DEFAULT_MODEL` in `.env`, restart — it works with Claude/Groq/Gemini with zero code changes.
6. **They inspect a trace** — they see the full graph tree, the safety guardrail using an orq.ai evaluator (not OpenAI moderation), and can drill into costs per span.

If all six pass, this repo becomes the canonical "how to build agents on orq.ai" reference.

---

## Plan file location

This plan will also be copied to `plans/repo-improvements.md` in the repo so it can be tracked alongside execution (following the pattern of `plans/manage-prompts-on-orq.md` and the deleted ChromaDB plan).
