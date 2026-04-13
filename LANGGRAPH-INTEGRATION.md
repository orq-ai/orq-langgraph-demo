# LangGraph ↔ orq.ai Integration

This repo ships **two** working integrations between LangGraph and orq.ai. Both
capture the full LangGraph execution tree (nodes, tool calls, LLM calls) and
send it to orq.ai's Traces view. They differ in *how* the spans get there.

Pick one with `ORQ_TRACING_BACKEND` in `.env`:

| Value       | Backend                                                   |
|-------------|-----------------------------------------------------------|
| `callback`  | `orq_ai_sdk.langchain` callback handler (default)         |
| `otel`      | OpenTelemetry exporter → orq.ai's OTLP endpoint           |
| `none`      | Logging only — no spans sent                              |

Both backends are kept side by side as educational reference. If you're
building a new LangGraph app on orq.ai, **the callback backend is what you
want** — it's simpler, has no env-var conflicts with LangSmith, and auto-flushes
on interpreter shutdown. The OTEL backend exists because it's worth knowing how
the underlying protocol works, and because it gives you full OTEL-API access
for custom span attributes.

## Backend 1: Callback handler (default)

**How to enable:**
```bash
# .env
ORQ_TRACING_BACKEND="callback"
```

**What it does:** `orq_ai_sdk.langchain.setup(api_key=...)` creates an
`OrqLangchainCallback` (a LangChain `BaseCallbackHandler`) and stores it in a
module-level `ContextVar`. The SDK's `__init__.py` registers that ContextVar
with LangChain via `langchain_core.tracers.context.register_configure_hook`,
so every Runnable invocation — at every nesting depth — picks up the handler
automatically. LangGraph is built on top of LangChain Runnables, so every
node, tool call, and LLM call in the graph emits spans without any per-call
wiring.

**Where spans go:** the callback builds OTLP-formatted span dicts and POSTs
them as batched envelopes to `https://my.orq.ai/v2/otel/v1/traces`. The SDK's
`OrqTracesClient` (`orq_ai_sdk/langchain/_client.py`) debounces spans on a
1-second timer so all spans from one trace arrive in a single request, and it
registers its own `atexit` drain so short-lived scripts (like the eval
pipeline) don't lose the final batch.

**Implementation in this repo:** `src/assistant/tracing_callback.py` — about
15 lines. Idempotency check uses the SDK's own `_handler_var` as source of
truth.

## Backend 2: OpenTelemetry exporter

**How to enable:**
```bash
# .env
ORQ_TRACING_BACKEND="otel"
```

**What it does:** bridges LangChain's built-in LangSmith integration to an
OTEL exporter by setting six environment variables:

```python
os.environ["LANGSMITH_OTEL_ENABLED"]       = "true"
os.environ["LANGSMITH_TRACING"]            = "true"
os.environ["LANGSMITH_OTEL_ONLY"]          = "true"   # prevents double tracing
os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"]  = "https://api.orq.ai/v2/otel"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"]   = f"Authorization=Bearer {ORQ_API_KEY}"
```

LangChain sees `LANGSMITH_TRACING=true` and tries to emit trace data to
LangSmith; `LANGSMITH_OTEL_ENABLED` + `LANGSMITH_OTEL_ONLY` tell it to route
through OTEL instead. The OTEL exporter then ships spans to orq.ai's OTLP
endpoint.

On top of that, this backend creates a `TracerProvider`, attaches a
`BatchSpanProcessor(OTLPSpanExporter())`, and registers an `atexit` hook that
calls `provider.force_flush(timeout_millis=10_000)` — short-lived scripts like
`evals/run_evals.py` would otherwise lose spans to the BatchSpanProcessor's
internal debounce.

**Implementation in this repo:** `src/assistant/tracing_otel.py`.

## Pros and cons

| Aspect                            | Callback                                              | OTEL                                                     |
|-----------------------------------|-------------------------------------------------------|----------------------------------------------------------|
| Setup complexity                  | One `setup(api_key=…)` call                           | 6 env vars + `TracerProvider` + `BatchSpanProcessor` + exporter + atexit |
| Span coverage                     | Every LangChain Runnable (LangGraph nodes, tools, LLMs) | Same — plus any other OTEL-instrumented library in the process |
| Flush on interpreter exit         | SDK's `OrqTracesClient` registers its own `atexit` drain | `BatchSpanProcessor.force_flush` in our own `atexit`     |
| Custom span attributes            | Limited to what the SDK handler exposes               | Full OTEL API — grab the current span and `set_attribute()` from anywhere |
| Vendor coupling                   | High — handler is orq-specific                        | Low — OTLP is a standard, you can repoint the exporter   |
| Upgrade path                      | New SDK versions ship handler improvements automatically | OTEL APIs are stable; endpoint changes need env-var edits |
| Import-order requirement          | `setup_tracing()` before any `Runnable.invoke()`      | `setup_tracing()` before any `import langchain` (env-var stomp) |
| LangSmith env-var conflicts       | None — fully orthogonal                               | Requires `LANGSMITH_OTEL_ONLY=true` to avoid double tracing |
| Lines of code in this repo        | ~15                                                   | ~40                                                      |

### When to pick which

- **Pick `callback`** if you're building a new LangGraph app on orq.ai and
  just want spans in Studio. It's the happy path and the default.
- **Pick `otel`** if you already have OTEL infrastructure you want to feed
  (you can swap the exporter for a different endpoint), or if you need the
  full OTEL SDK to attach custom attributes to spans from non-LangChain code
  paths.
- **Pick `none`** when running the doctor, bootstrap scripts, or anything
  where you don't want trace noise in Studio.

## How to switch

1. Edit `.env` and set `ORQ_TRACING_BACKEND` to one of the three values.
2. Restart the entry point (`make chat`, `make evals`, etc.).

That's the whole switch. The two backends are mutually exclusive — we set up
one or the other, never both — so there's no double-tracing risk.

Note: the `LANGSMITH_*` and `OTEL_*` env vars are **only** set when the OTEL
backend is active. If you switch to `callback`, those env vars stop being
touched, so if you have stale values lingering from a previous OTEL run they
won't interfere with the callback path (the callback handler ignores them
entirely).

## Troubleshooting

For the OTEL backend specifically — fragmented traces, `LANGSMITH_OTEL_ENABLED`
gotchas, and the import-order requirement — see the "OpenTelemetry tracing"
section in [TROUBLESHOOTING.md](./TROUBLESHOOTING.md).

For the callback backend, if spans aren't showing up in Studio:

1. Confirm `ORQ_TRACING_BACKEND="callback"` is set in `.env` and nothing else
   overrides it in the shell environment.
2. Confirm `ORQ_API_KEY` is set — `setup_callback_tracing()` raises
   `RuntimeError` if it's missing.
3. Confirm `ORQ_DISABLE_TRACING` is `1` — the dispatcher sets this via
   `os.environ.setdefault` to prevent `evaluatorq` from registering a second
   tracer that would intercept your spans.
4. Check the orq.ai Studio Traces tab with a time filter set to the last few
   minutes — the callback handler's 1-second debounce + batch upload means
   very recent spans appear with a short delay.

## Reference

- Callback backend: `src/assistant/tracing_callback.py`
- OTEL backend: `src/assistant/tracing_otel.py`
- Dispatcher (public API): `src/assistant/tracing.py`
- Setting: `src/core/settings.py` → `ORQ_TRACING_BACKEND`
- Upstream SDK integration: `orq_ai_sdk/langchain/_global.py`, `_handler.py`, `_client.py`
