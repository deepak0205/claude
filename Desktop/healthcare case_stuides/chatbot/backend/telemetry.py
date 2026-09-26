"""OpenTelemetry setup, ported from agent_poc/config/telemetry.py. No-op unless OTEL_ENABLED."""
import functools
import time
from collections.abc import Callable

from backend.config import settings

_tracer = None
_llm_call_counter = None
_retrieval_latency_histogram = None


def init_telemetry() -> None:
    global _tracer, _llm_call_counter, _retrieval_latency_histogram
    if not settings.otel_enabled:
        return

    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": settings.otel_service_name})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    _tracer = trace.get_tracer(settings.otel_service_name)

    meter = metrics.get_meter(settings.otel_service_name)
    _llm_call_counter = meter.create_counter("llm_call_count", description="Number of LLM calls")
    _retrieval_latency_histogram = meter.create_histogram(
        "retrieval_latency_ms", description="RAG retrieval latency in ms"
    )


def traced(span_name: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not settings.otel_enabled or _tracer is None:
                return fn(*args, **kwargs)
            start = time.perf_counter()
            with _tracer.start_as_current_span(span_name):
                result = fn(*args, **kwargs)
            elapsed_ms = (time.perf_counter() - start) * 1000
            if _retrieval_latency_histogram is not None and span_name == "rag.retrieve":
                _retrieval_latency_histogram.record(elapsed_ms)
            return result
        return wrapper
    return decorator


def record_llm_call() -> None:
    if _llm_call_counter is not None:
        _llm_call_counter.add(1)
