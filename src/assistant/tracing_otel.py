"""OpenTelemetry tracing backend.

Routes LangGraph spans to orq.ai's OTLP endpoint via LangChain's built-in
LangSmith → OTEL bridge. Selected when ``ORQ_TRACING_BACKEND="otel"``.

This is the original integration approach for the repo. The newer callback-
handler backend (``tracing_callback.py``) is the default; this module is kept
for educational reference and as a fallback. See ``LANGGRAPH-INTEGRATION.md``
for the tradeoffs.
"""

import atexit
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_otel_tracing() -> None:
    """Configure the OTEL → orq.ai exporter. Idempotent.

    Stomps six environment variables that wire LangChain's LangSmith
    integration to emit OTLP spans instead of LangSmith API calls. This must
    run before any ``langchain`` module is imported, which is why every entry
    point calls ``setup_tracing()`` at module top.
    """
    # OTEL is the source of truth. Before set_tracer_provider() is called,
    # get_tracer_provider() returns a ProxyTracerProvider — not a real SDK
    # TracerProvider — so this isinstance check cleanly detects whether
    # setup has already run.
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return

    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.orq.ai/v2/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Bearer {os.getenv('ORQ_API_KEY')}"

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    # Flush pending spans on process exit so short-lived scripts (eval
    # pipeline, doctor) don't lose trace data to BatchSpanProcessor's debounce.
    atexit.register(_flush_on_exit)


def _flush_on_exit() -> None:
    """Force-flush pending OTEL spans to orq.ai on process exit."""
    provider = trace.get_tracer_provider()
    if isinstance(provider, TracerProvider):
        provider.force_flush(timeout_millis=10_000)
