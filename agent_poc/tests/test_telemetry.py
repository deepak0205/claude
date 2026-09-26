"""Tests for config/telemetry.py.

`init_telemetry()` is never exercised against a real OTLP endpoint here —
`settings.OTEL_ENABLED` defaults to `False` in every other test in this
repo, so `config.telemetry`'s module-level `tracer`/`meter` resolve against
the OTel API's own no-op implementation and every other test stays mock-free
(per the module + addendum docstrings). This file instead:

1. Proves `traced` is transparent to return values and re-raises exceptions
   unchanged (critical for `agents/base_subagent.py`'s and
   `agents/memory.py`'s own blanket `try/except`).
2. Installs a *test-local* OTel SDK TracerProvider (InMemorySpanExporter +
   SimpleSpanProcessor) to prove a `@traced`-wrapped function produces a
   real span with the right name/attributes when a provider is actually
   registered — without touching the module's own OTLP setup.
3. Exercises `record_llm_usage` against a test-local in-memory metric
   reader, asserting the right counts land.
"""

from types import SimpleNamespace

import pytest
from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)

from config.telemetry import record_llm_usage, traced


def test_traced_passes_through_return_value():
    @traced("test.some_function")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_traced_reraises_exceptions_unchanged():
    @traced("test.failing_function")
    def boom():
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        boom()


def test_traced_produces_real_spans_for_success_and_error_cases():
    # The OTel API only allows the global TracerProvider to be set once per
    # process (later calls are silently ignored with a warning) — so both
    # the success-span and error-span assertions share one provider/exporter
    # registered exactly once here, rather than each having their own.
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    previous_provider = trace.get_tracer_provider()
    trace.set_tracer_provider(provider)
    try:
        # config.telemetry.tracer was created via trace.get_tracer(...) at
        # import time; the OTel API's tracer proxy resolves against
        # whatever provider is globally registered *at call time*, so
        # re-pointing the global provider here is enough to make the
        # already-imported `tracer`/`traced` pick it up.
        @traced("test.dummy_span", agent_name="literature", selected=True)
        def dummy(x):
            return x * 2

        result = dummy(21)

        assert result == 42
        spans = exporter.get_finished_spans()
        assert len(spans) == 1
        span = spans[0]
        assert span.name == "test.dummy_span"
        assert span.attributes["agent_name"] == "literature"
        assert span.attributes["selected"] is True

        exporter.clear()

        @traced("test.dummy_error_span")
        def boom():
            raise RuntimeError("nope")

        with pytest.raises(RuntimeError, match="nope"):
            boom()

        error_spans = exporter.get_finished_spans()
        assert len(error_spans) == 1
        error_span = error_spans[0]
        assert error_span.status.status_code.name == "ERROR"
        assert len(error_span.events) == 1
        assert error_span.events[0].name == "exception"
    finally:
        trace.set_tracer_provider(previous_provider)


def test_record_llm_usage_increments_call_and_token_counters():
    reader = InMemoryMetricReader()
    provider = MeterProvider(metric_readers=[reader])

    previous_provider = metrics_get_provider()
    set_meter_provider(provider)
    try:
        response = SimpleNamespace(usage=SimpleNamespace(input_tokens=100, output_tokens=25))
        record_llm_usage(response, model="claude-sonnet-5", function="call_tool")
    finally:
        set_meter_provider(previous_provider)

    data = reader.get_metrics_data()
    metrics_by_name = {}
    for rm in data.resource_metrics:
        for sm in rm.scope_metrics:
            for m in sm.metrics:
                metrics_by_name.setdefault(m.name, []).extend(m.data.data_points)

    call_points = metrics_by_name["agentic_rag.llm.calls"]
    assert any(
        p.attributes.get("model") == "claude-sonnet-5" and p.attributes.get("function") == "call_tool"
        for p in call_points
    )

    token_points = metrics_by_name["agentic_rag.llm.token_usage"]
    input_point = next(p for p in token_points if p.attributes.get("token_type") == "input")
    output_point = next(p for p in token_points if p.attributes.get("token_type") == "output")
    assert input_point.value == 100
    assert output_point.value == 25


def metrics_get_provider():
    from opentelemetry import metrics

    return metrics.get_meter_provider()


def set_meter_provider(provider):
    from opentelemetry import metrics

    metrics.set_meter_provider(provider)
