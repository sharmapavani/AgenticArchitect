"""OpenTelemetry SDK initialization (traces + metrics)."""

from __future__ import annotations

import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_initialized = False


def is_otel_enabled() -> bool:
    return os.getenv("OTEL_ENABLED", "0").strip().lower() in {"1", "true", "yes"}


def init_otel(service_name: str | None = None) -> None:
    """Configure TracerProvider and MeterProvider with OTLP HTTP exporters."""
    global _initialized
    if _initialized or not is_otel_enabled():
        return

    resolved_name = service_name or os.getenv("OTEL_SERVICE_NAME", "multiagentchat")
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318").rstrip(
        "/"
    )
    traces_url = f"{endpoint}/v1/traces"
    metrics_url = f"{endpoint}/v1/metrics"

    resource = Resource.create({"service.name": resolved_name})

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_url))
    )
    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=metrics_url),
        export_interval_millis=int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MS", "5000")),
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    _initialized = True


def get_tracer(name: str = "multiagentchat"):
    return trace.get_tracer(name)


def flush_telemetry(timeout_millis: int = 5000) -> None:
    """Flush pending traces and metrics to the collector."""
    if not is_otel_enabled():
        return
    trace_provider = trace.get_tracer_provider()
    if hasattr(trace_provider, "force_flush"):
        trace_provider.force_flush(timeout_millis=timeout_millis)
    meter_provider = metrics.get_meter_provider()
    if hasattr(meter_provider, "force_flush"):
        meter_provider.force_flush(timeout_millis=timeout_millis)
