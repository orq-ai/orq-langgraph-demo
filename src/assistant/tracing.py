"""Orq.ai tracing configuration for LangGraph observability.

Uses OpenTelemetry (OTEL) to capture LangGraph traces and auto-register assets
(agents, tools, models) in the orq.ai Control Tower.
"""

import atexit
import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_provider: TracerProvider | None = None


def setup_tracing():
    """Configure OpenTelemetry to export LangGraph traces to orq.ai Control Tower."""
    global _provider
    if _provider is not None:
        return

    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.orq.ai/v2/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Bearer {os.getenv('ORQ_API_KEY')}"

    _provider = TracerProvider()
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(_provider)

    # Flush pending spans on process exit so short-lived scripts
    # (like the eval pipeline) don't lose trace data.
    atexit.register(flush_tracing)


def flush_tracing() -> None:
    """Force-flush pending OTEL spans to orq.ai."""
    if _provider is not None:
        _provider.force_flush(timeout_millis=10_000)
