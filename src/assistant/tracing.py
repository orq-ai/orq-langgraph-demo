"""Orq.ai tracing configuration for LangGraph observability.

Uses OpenTelemetry (OTEL) to capture LangGraph traces and auto-register assets
(agents, tools, models) in the orq.ai Control Tower. Also quiets a handful of
noisy third-party loggers so terminal output stays readable across every
entry point (Chainlit, evals, bootstrap, doctor).
"""

import atexit
import logging
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

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


def setup_tracing() -> None:
    """Configure OpenTelemetry + quiet noisy third-party loggers.

    Idempotent: safe to call from every entry point. The OTEL setup uses
    the global `TracerProvider` as its source of truth so a second call
    becomes a no-op.
    """
    # Quiet noisy loggers unconditionally — even on the second call, in
    # case another module bumped them back to INFO after us.
    for name, level in _NOISY_LOGGERS.items():
        logging.getLogger(name).setLevel(level)

    # OTEL is the source of truth. Before set_tracer_provider() is called,
    # get_tracer_provider() returns a ProxyTracerProvider — not a real
    # SDK TracerProvider — so this isinstance check cleanly detects
    # whether setup has already run.
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return

    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.orq.ai/v2/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Bearer {os.getenv('ORQ_API_KEY')}"
    # Prevent evaluatorq from registering its own TracerProvider — OTEL allows
    # only one global provider, and ours is the one LangGraph spans flow through.
    os.environ["ORQ_DISABLE_TRACING"] = "1"

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    # Flush pending spans on process exit so short-lived scripts
    # (like the eval pipeline) don't lose trace data.
    atexit.register(_flush_on_exit)


def _flush_on_exit() -> None:
    """Force-flush pending OTEL spans to orq.ai on process exit."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.force_flush(timeout_millis=10_000)
