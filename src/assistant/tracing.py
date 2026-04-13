"""Tracing dispatcher for the Hybrid Data Agent.

Routes LangGraph spans to one of two orq.ai integrations based on the
``ORQ_TRACING_BACKEND`` setting:

- ``callback`` (default) — registers ``orq_ai_sdk.langchain``'s callback
  handler, which auto-traces every LangChain Runnable. See
  ``tracing_callback.py``.
- ``otel`` — bridges LangSmith → OTLP → orq.ai's OTEL endpoint via the
  OpenTelemetry SDK. See ``tracing_otel.py``.
- ``none`` — no tracing; only quiets noisy third-party loggers so terminal
  output stays readable.

Both backends are ship as educational reference. ``LANGGRAPH-INTEGRATION.md``
at the repo root walks through the tradeoffs.

The public entry point is ``setup_tracing()``. Every entry point in the repo
(Chainlit apps, eval pipeline) calls it at module top — keep that pattern, as
the OTEL backend's env-var stomp must precede any ``langchain`` import.
"""

import logging
import os

from core.settings import settings

# Third-party loggers that default to INFO and flood the terminal with one
# line per HTTP call or one warning per LangChain callback. Quieted centrally
# so every entry point inherits the same clean defaults.
_NOISY_LOGGERS = {
    "httpx": logging.WARNING,
    "openai": logging.WARNING,
    "openai._base_client": logging.WARNING,
    # LangChain's built-in tracer occasionally fails to serialize a
    # ModelMetaclass in LLM response metadata — non-fatal, but noisy.
    "langchain_core.callbacks.manager": logging.ERROR,
}


def quiet_noisy_loggers() -> None:
    """Bump noisy third-party loggers down to WARNING/ERROR.

    Run unconditionally, even on the second call — another module may have
    bumped them back to INFO after us.
    """
    for name, level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(level)


def setup_tracing() -> None:
    """Configure tracing per ``settings.ORQ_TRACING_BACKEND``.

    Idempotent — each backend self-checks and short-circuits on re-entry.
    Safe to call from every entry point. The settings field is a ``Literal``
    so pydantic rejects bad backend values at process start; no defensive
    branching needed here.
    """
    quiet_noisy_loggers()

    # evaluatorq registers its own TracerProvider on import. Disable it
    # regardless of which backend we picked so eval runs never get
    # double-traced. Use setdefault so an explicit user override wins.
    os.environ.setdefault("ORQ_DISABLE_TRACING", "1")

    backend = settings.ORQ_TRACING_BACKEND
    if backend == "callback":
        from .tracing_callback import setup_callback_tracing

        setup_callback_tracing()
    elif backend == "otel":
        from .tracing_otel import setup_otel_tracing

        setup_otel_tracing()
    # backend == "none" → only the logger-quieting above runs.
