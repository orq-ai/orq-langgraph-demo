# Plan: Manage prompts on orq.ai for versioning & A/B testing

> **Status: Phase A complete** — `get_system_prompt()` fetcher with fallback is in `src/assistant/prompts.py`, wired via `default_factory` in `src/assistant/context.py`. Bootstrap handled by `scripts/setup_orq_workspace.py` (run via `make setup-workspace`). Phase B (remaining 3 prompts + environment tags + A/B experiments) not yet started.

## Context

The RAG agent currently stores all system prompts as hardcoded Python strings in `src/assistant/prompts.py`:

- `SYSTEM_PROMPT` (~65 lines) — main tool-calling agent prompt with RAG grounding rules
- `ROUTER_SYSTEM_PROMPT` — query classifier
- `MORE_INFO_SYSTEM_PROMPT` — clarification node
- `GENERAL_SYSTEM_PROMPT` — off-topic redirect node

These are wired through `Context` in `src/assistant/context.py` as overridable fields, so the architecture already supports runtime replacement — we just need to plug in a fetcher.

**Goal:** move prompts to orq.ai so product/content folks can version, edit, and A/B test them without code changes, while keeping the local strings as a fallback for offline development.

**Reference docs:** https://docs.orq.ai/docs/prompts/overview and https://docs.orq.ai/docs/prompts/api-usage

---

## Why this fits

1. **Versioning & rollback** — Prompt changes live in the orq.ai Studio version history, not git. Revert with one click.
2. **Variable interpolation** — `SYSTEM_PROMPT` has `{system_time}`, routing prompts have `{logic}`. orq.ai supports `{{var}}` templating (Text/Jinja/Mustache), which maps directly.
3. **Environment tags** — Tag versions with `production` / `staging` and reference via `@production`, etc. Promote between environments in the UI.
4. **Closes the eval loop** — evaluatorq experiments already run on orq.ai. With versioned prompts, we can A/B compare two prompt versions against the same dataset + scorers.
5. **Trace linkage** — Traces already capture which prompt version rendered the span, making debugging across versions much easier.

---

## Phased approach

### Phase A (proof of value): Migrate `SYSTEM_PROMPT` only

The main system prompt is the biggest, changes most often, and has the highest evaluation leverage. Router/more-info/general prompts stay in code for now.

### Phase B (after Phase A proves out): Migrate remaining prompts

Move `ROUTER_SYSTEM_PROMPT`, `MORE_INFO_SYSTEM_PROMPT`, `GENERAL_SYSTEM_PROMPT`, add environment tags, and set up a prompt A/B experiment with evaluatorq.

---

## Phase A: Migrate `SYSTEM_PROMPT`

### Step 1 — Create the prompt in orq.ai Studio

- Project: `langgraph-demo` (per `ORQ_PROJECT_NAME`)
- Key: `hybrid-data-agent-system-prompt`
- Template engine: **Text** (same `{{var}}` syntax as our current `.format()` placeholders, minus the single braces)
- Content: paste the body of `SYSTEM_PROMPT` from `src/assistant/prompts.py:3-67`
- Change `{system_time}` → `{{system_time}}` in the orq.ai version so it uses orq.ai's templating

Publish as v1.

### Step 2 — Add a fetcher to `src/assistant/prompts.py`

The SDK exposes `client.prompts.retrieve(id=...)` and `client.prompts.list(limit=...)`. Since `retrieve` takes an ID (not a key), we need to either:

- **Option A:** Store the prompt ID in `.env` as `ORQ_SYSTEM_PROMPT_ID` after creation (simpler, no extra API call)
- **Option B:** List prompts on first fetch, find the one with matching `key`, cache the ID (more ergonomic, one extra API call on first run)

**Recommendation: Option A** for Phase A — simpler, matches how we handle `ORQ_KNOWLEDGE_BASE_ID`.

Add to `src/core/settings.py`:
```python
ORQ_SYSTEM_PROMPT_ID: str = Field(
    default="",
    description="orq.ai prompt ID for the main system prompt (leave empty to use the local fallback)",
    env="ORQ_SYSTEM_PROMPT_ID",
)
```

Add to `src/assistant/prompts.py`:
```python
from functools import lru_cache

SYSTEM_PROMPT = """... existing hardcoded string (kept as fallback) ..."""


@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """Return the system prompt, fetched once per process from orq.ai when configured.

    Falls back to the hardcoded SYSTEM_PROMPT if ORQ_API_KEY or
    ORQ_SYSTEM_PROMPT_ID are unset, or if the fetch fails.
    """
    from core.settings import settings

    if not settings.ORQ_SYSTEM_PROMPT_ID:
        return SYSTEM_PROMPT

    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        return SYSTEM_PROMPT

    try:
        from orq_ai_sdk import Orq
        with Orq(api_key=api_key) as client:
            response = client.prompts.retrieve(id=settings.ORQ_SYSTEM_PROMPT_ID)
            return _extract_prompt_text(response)
    except Exception as e:
        logger.warning(f"Failed to fetch system prompt from orq.ai, using fallback: {e}")
        return SYSTEM_PROMPT


def _extract_prompt_text(response) -> str:
    """Extract the system message text from an orq.ai prompt retrieve response."""
    # The exact shape depends on the SDK — inspect at implementation time.
    # Typically: response.version.messages[0].content where role == "system"
    ...
```

`lru_cache(maxsize=1)` ensures we hit orq.ai **once per process**, not per graph invocation. Chainlit sessions share the same process so this is fine.

### Step 3 — Update `src/assistant/context.py`

```python
from . import prompts

@dataclass
class Context:
    system_prompt: str = field(
        default_factory=prompts.get_system_prompt,  # call the fetcher on Context init
        metadata={...},
    )
```

Switching from `default=prompts.SYSTEM_PROMPT` to `default_factory=prompts.get_system_prompt` means each new `Context()` triggers the cached fetch (first call hits the network, subsequent calls are free).

### Step 4 — Template variable rename

The current code uses `.format(system_time=...)` with single-brace `{system_time}`. orq.ai Text engine uses `{{system_time}}`. Two options:

- **Option A:** Change the template in orq.ai to `{{system_time}}` and update the caller to render it via `Template` / str replace
- **Option B:** When fetching, post-process the response to convert `{{system_time}}` → `{system_time}` so `.format()` still works unchanged

**Recommendation: Option B** — zero changes at the call sites, the fetcher handles the conversion.

### Step 5 — Verification

- Run with `ORQ_SYSTEM_PROMPT_ID` unset: confirm the local fallback is used (check logs)
- Run with `ORQ_SYSTEM_PROMPT_ID` set to a valid ID: confirm the fetched prompt is used (log the first 100 chars on startup)
- Run the eval pipeline (`make evals-run`): confirm tool-accuracy scores are unchanged
- Edit the prompt in orq.ai Studio, publish a new version, restart the app, confirm the new version takes effect

---

## Phase B (future)

After Phase A proves out:

1. Migrate `ROUTER_SYSTEM_PROMPT`, `MORE_INFO_SYSTEM_PROMPT`, `GENERAL_SYSTEM_PROMPT` using the same pattern
2. Add a generic `get_prompt(setting_name: str, fallback: str) -> str` helper to avoid duplicating the fetch logic four times
3. Tag prompt versions with environments (`@production`, `@staging`)
4. Create an evaluatorq experiment that compares two prompt versions against the existing dataset, using the existing `tool-accuracy` / `category-accuracy` scorers

---

## Files to modify

| File | Change |
|---|---|
| `src/assistant/prompts.py` | Add `get_system_prompt()` fetcher with `lru_cache`, keep local `SYSTEM_PROMPT` as fallback |
| `src/assistant/context.py` | Switch `system_prompt` field to `default_factory=prompts.get_system_prompt` |
| `src/core/settings.py` | Add `ORQ_SYSTEM_PROMPT_ID` setting |
| `.env.example` | Document the new variable |

---

## Verification

1. **Fallback path:** Unset `ORQ_SYSTEM_PROMPT_ID`, run `make run`, confirm the app boots and responses are identical to the hardcoded prompt
2. **Fetched path:** Set `ORQ_SYSTEM_PROMPT_ID` to the new v1 ID, restart, confirm logs show the fetched prompt and responses still work
3. **Version rollout:** Edit the prompt in Studio, bump to v2, restart the app, confirm the new version is in effect (the `lru_cache` is per-process, so a restart is required — documented as expected)
4. **Offline dev:** Unset `ORQ_API_KEY`, confirm the app still runs using the fallback
5. **Eval unchanged:** `make evals-run` should produce the same scores as before the migration (we're serving the same prompt text, just from a different source)

---

## Risks

1. **Drift between `prompts.py` and orq.ai Studio** — If someone edits both, they diverge. Mitigation: designate orq.ai Studio as canonical, and add a comment on the local `SYSTEM_PROMPT` marking it as a fallback.
2. **Lost git audit trail** — Prompt changes no longer show in PRs. Mitigation: orq.ai version history is the audit log, and experiments gate quality regressions.
3. **Network dependency on startup** — First `Context()` init hits orq.ai. Mitigation: fallback to local string on any exception; `lru_cache` limits the impact.
4. **Template engine mismatch** — Current code uses Python `str.format()` with `{var}`, orq.ai uses `{{var}}`. Mitigation: post-process the fetched text in Step 4 Option B.
