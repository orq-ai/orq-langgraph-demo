# Troubleshooting

## Always start with `make doctor`

```bash
make doctor
```

This is the first thing to run when anything feels off. It walks every
moving piece of the setup in order and prints `✓` / `✗` per check with a
clear remediation for each failure, so you don't have to guess where the
break is. What it checks (see [`scripts/doctor.py`](scripts/doctor.py)):

| # | Check | What a failure means |
|---|---|---|
| 1 | `.env` parses cleanly | A malformed line (pasted script output, missing `=`) is breaking `python-dotenv` |
| 2 | `OPENAI_API_KEY` reaches `/v1/models` | Key missing, revoked, or out of quota |
| 3 | `ORQ_API_KEY` reaches `/v2/projects` | Key missing or revoked |
| 4 | `ORQ_PROJECT_NAME` exists on orq.ai | You haven't run `make setup-workspace` yet, or the project was renamed |
| 5 | Knowledge Base is reachable and has chunks | You haven't run `make ingest-kb`, or the KB ID in `.env` points at a deleted KB |
| 6 | System prompt is fetchable | `ORQ_SYSTEM_PROMPT_ID` is stale or the prompt was deleted in the Studio |
| 7 | A test KB search returns matches | Ingestion finished uploading but chunks are still being embedded — wait ~1 minute and re-run |
| 8 | SQLite sales DB exists and has rows | You haven't run `make ingest-sql` |
| 9 | `evaluatorq` is importable | The `eval` dependency group isn't synced — run `uv sync --group eval` |

If every check passes but you're still seeing weird behaviour, the issues
below are the ones that are **not** caught by `make doctor` — mostly tracing
wiring and `.env` parsing edge cases worth knowing about.

> **Pointing at a non-production orq.ai endpoint?** Set `ORQ_API_BASE` in
> `.env` (default `https://api.orq.ai/v2`). Every call — Router, KB search,
> prompts, managed-agent invocation, doctor, setup-workspace — routes
> through that base URL.

Tracing is the one subsystem `make doctor` can't fully validate — spans
flush asynchronously and symptoms only show up in the orq.ai Studio Traces
tab after the fact. Which gotcha you hit depends on which backend you're
running (`ORQ_TRACING_BACKEND` in `.env`); the sections below are split
accordingly. For the backend comparison and how to switch, see
[LANGGRAPH-INTEGRATION.md](LANGGRAPH-INTEGRATION.md).

---

## Callback backend (`ORQ_TRACING_BACKEND="callback"`, default)

The callback path registers `orq_ai_sdk.langchain`'s handler via LangChain's
configure-hook system. It's much simpler than the OTEL path, so there are
only a couple of failure modes worth knowing about.

### Spans don't appear in the Studio Traces tab

**Symptom:** you run the Chainlit app or `make evals`, the agent answers
fine, but the Traces tab shows nothing for the latest runs.

**Checklist:**

1. Confirm the backend is actually `callback` — `echo $ORQ_TRACING_BACKEND`
   or check `.env`. If a shell export overrides `.env`, the dispatcher picks
   the shell value.
2. Confirm `ORQ_API_KEY` is set. `setup_callback_tracing()` raises
   `RuntimeError` on missing key, so if startup crashed with that message,
   that's the reason.
3. Wait ~2 seconds before checking the Traces tab. The SDK's `OrqTracesClient`
   debounces span uploads on a 1-second timer and batches a whole trace into
   one OTLP envelope — very recent spans have a short delay.
4. Confirm `ORQ_DISABLE_TRACING=1` is set. The dispatcher sets it via
   `os.environ.setdefault` to stop `evaluatorq` from registering a second
   tracer that would swallow your spans. If another module set it to `"0"`
   or `""` earlier, that wins — check your env vars.

### Spans appear in the wrong orq.ai project

**Symptom:** spans are in Studio but under `Default` instead of the project
your `ORQ_PROJECT_NAME` points to.

**Root cause:** the orq.ai API key you're using is scoped to a different
project than `ORQ_PROJECT_NAME`. Project-scoped keys route traces to their
bound project regardless of what you configured.

**Fix:** same as the resource-routing gotcha — generate a workspace-level
API key in the Studio, or set `ORQ_PROJECT_NAME` to match the key's bound
project.

---

## OpenTelemetry backend (`ORQ_TRACING_BACKEND="otel"`)

> **Applies only when you've explicitly switched to the OTEL backend.** The
> default (`callback`) is not affected by any of the gotchas in this section.

Three gotchas we hit when the OTEL path was our primary integration:

### Traces appear fragmented / flat (individual LLM spans, no graph tree)

**Symptom:** In orq.ai Studio → Traces you see individual `ChatOpenAI` spans but no parent `Hybrid Data Agent` / `call_model` / `tools` hierarchy.

**Root cause:** The `BatchSpanProcessor` queues spans and flushes them asynchronously. In short-lived scripts (like `make evals-run`) the process exits before the queue drains, so spans are dropped or arrive without their parent context.

**Fix:** Register an `atexit` handler that force-flushes on process exit. Read the provider from OTEL's own global registry rather than keeping a shadow reference — OTEL is already the source of truth:
```python
import atexit
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

def _flush_on_exit() -> None:
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        current.force_flush(timeout_millis=10_000)

atexit.register(_flush_on_exit)
```

See [`src/assistant/tracing_otel.py`](src/assistant/tracing_otel.py).

### `LANGSMITH_OTEL_ENABLED` is required for LangGraph traces

**Symptom:** You set up the OTEL exporter but LangGraph nodes never appear as spans.

**Root cause:** LangChain/LangGraph's built-in tracer is **off by default**. The three env vars that turn it on also look like they route to LangSmith — but with `LANGSMITH_OTEL_ONLY=true` they route to the OTEL exporter (i.e. *your* orq.ai endpoint) instead of LangSmith.

**Required setup** (see [`src/assistant/tracing_otel.py`](src/assistant/tracing_otel.py)):
```python
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_OTEL_ONLY"] = "true"
```

Despite the naming, nothing is ever sent to LangSmith with this combination.

### Import order matters: setup tracing **before** importing langchain/evaluatorq

**Symptom:** Traces from the eval pipeline appear incomplete while traces from Chainlit look fine.

**Root cause:** LangSmith's OTEL hooks register with whatever `TracerProvider` is the global default at the time langchain is first imported. If you `import langchain_core` before calling `setup_tracing()`, the hooks register against the default no-op provider and never see your real exporter.

**Fix:** Always call `setup_tracing()` **before** importing anything that transitively pulls in `langchain_core`, `langsmith`, or `evaluatorq`. See the import order in [`evals/run_evals.py`](evals/run_evals.py):
```python
load_dotenv()
from assistant.tracing import setup_tracing  # noqa: E402
setup_tracing()
from evaluatorq import ...  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
```

---

## Getting help

If `make doctor` is green but something still isn't right:

1. **Check the orq.ai Studio** for the failing entity (trace, KB, dataset) — error context is usually clearer there than in logs.
2. **Check the span tree** — if the agent misbehaves, the full LangGraph execution tree in the Traces tab will show exactly which node produced the bad output.
3. **File an issue** on this repo describing the symptom and what `make doctor` reported.
