"""OpenTelemetry SDK setup — tracing + metrics — for every other module in
this project.

Deliberately minimal for the POC, mirroring `agents/llm.py`'s lazy-singleton
style: `init_telemetry()` wires up the SDK (`TracerProvider`/`MeterProvider`
exporting OTLP to `settings.OTEL_EXPORTER_OTLP_ENDPOINT`) exactly once, and
is called at import time below. When `settings.OTEL_ENABLED` is `False` (the
default), `init_telemetry()` is a no-op and the `opentelemetry-api`'s own
no-op implementation handles every `tracer`/`meter` call transparently — no
exporter, no background thread, no network activity, and critically, no test
mocking required anywhere else in the codebase.

`traced(span_name, **static_attributes)` is the one decorator every other
module applies directly above a function definition, following the
`@_retry_on_transient`-style plain-callable-decorator idiom already used in
`ingestion/pubmed_client.py` and friends. It never swallows exceptions —
`agents/base_subagent.py`'s `run()` and `agents/memory.py`'s
`contextualize_query()` each have their own blanket `try/except` downstream
that must keep seeing the original exception unchanged.
"""

import functools
import time

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from config.settings import settings

_initialized = False


def init_telemetry() -> None:
    """Wire up the OTel SDK's global tracer/meter providers, once.

    No-op (idempotent, and a no-op entirely) unless `settings.OTEL_ENABLED`
    is `True` — see module docstring for why that keeps every other test in
    this repo mock-free.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    if not settings.OTEL_ENABLED:
        return

    resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT))
    )
    trace.set_tracer_provider(tracer_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT),
        export_interval_millis=settings.OTEL_METRICS_EXPORT_INTERVAL_MS,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)


# Module-level tracer/meter, safe to import anywhere before or after
# `init_telemetry()` runs — the OTel API returns a proxy that resolves
# against whatever provider is globally registered at call time.
tracer = trace.get_tracer("agentic-rag-poc")
meter = metrics.get_meter("agentic-rag-poc")


def traced(span_name: str, **static_attributes):
    """Decorator: wrap a function call in a span named `span_name` carrying
    `static_attributes`. Records + re-raises exceptions; never swallows
    them (see module docstring)."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # `start_as_current_span` already records the exception event and
            # sets ERROR status by default when an exception propagates out
            # of this block (record_exception=True, set_status_on_exception=
            # True) — no need to (and must not) do either manually, or the
            # exception event gets recorded twice. Re-raising unchanged is
            # what matters here: callers like `base_subagent.run()` and
            # `memory.contextualize_query()` have their own try/except that
            # must keep seeing the original exception.
            with tracer.start_as_current_span(span_name, attributes=static_attributes):
                return func(*args, **kwargs)

        return wrapper

    return decorator


# --- Shared metric instruments (agentic_rag.* naming) ---

llm_call_counter = meter.create_counter(
    "agentic_rag.llm.calls",
    description="Number of LLM (Anthropic Messages API) calls made.",
)
llm_token_usage_counter = meter.create_counter(
    "agentic_rag.llm.token_usage",
    description="Input/output token usage per LLM call, by model/function/token_type.",
)
tool_call_counter = meter.create_counter(
    "agentic_rag.tool.calls",
    description="Number of retrieval-tool invocations made by a sub-agent's tool-use loop.",
)
neo4j_query_duration_histogram = meter.create_histogram(
    "agentic_rag.neo4j.query_duration",
    description="Duration (seconds) of each Neo4j query run via rag.neo4j_client.run_query.",
    unit="s",
)
retrieval_result_count_histogram = meter.create_histogram(
    "agentic_rag.retrieval.result_count",
    description="Number of Evidence results returned by rag.retriever.hybrid_search.",
)
ingestion_stage_counter = meter.create_counter(
    "agentic_rag.ingestion.stage",
    description="Number of records fetched/loaded by an ingestion-pipeline function.",
)
memory_fold_counter = meter.create_counter(
    "agentic_rag.memory.folds",
    description="Number of times conversation-memory overflow turns were folded into the rolling summary.",
)


def record_llm_usage(response, model: str, function: str) -> None:
    """Record one LLM call's usage: increments `llm_call_counter` and pushes
    `response.usage.input_tokens`/`output_tokens` into
    `llm_token_usage_counter`, tagged by `model`, `function`, and
    `token_type` ("input"/"output")."""
    llm_call_counter.add(1, {"model": model, "function": function})

    usage = getattr(response, "usage", None)
    if usage is None:
        return

    input_tokens = getattr(usage, "input_tokens", None)
    if input_tokens is not None:
        llm_token_usage_counter.add(
            input_tokens, {"model": model, "function": function, "token_type": "input"}
        )

    output_tokens = getattr(usage, "output_tokens", None)
    if output_tokens is not None:
        llm_token_usage_counter.add(
            output_tokens, {"model": model, "function": function, "token_type": "output"}
        )


# Singleton-at-import, same pattern as `agents/llm.py`'s `client` and
# `rag/neo4j_client.py`'s lazy driver.
init_telemetry()
