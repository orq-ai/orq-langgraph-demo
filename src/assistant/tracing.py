"""Orq.ai tracing configuration for LangGraph observability.

Uses OpenTelemetry (OTEL) to capture LangGraph traces and auto-register assets
(agents, tools, models) in the orq.ai Control Tower.
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing():
    """Configure OpenTelemetry to export LangGraph traces to orq.ai Control Tower."""
    os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_OTEL_ONLY"] = "true"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "https://api.orq.ai/v2/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Bearer {os.getenv('ORQ_API_KEY')}"

    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)
