
import litellm
import logging
import os
import socket
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from traceloop.sdk import Traceloop

from opentelemetry._logs import set_logger_provider
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import SpanProcessor, TracerProvider as SDKTracerProvider

# Instrument httpx BEFORE litellm import — LiteLLM creates httpx clients at import time
HTTPXClientInstrumentor().instrument()

TENTANT_ID = "HPB_XXX_00001"

OTEL_COLLECTOR_ENDPOINT = os.environ.get("OTEL_COLLECTOR_ENDPOINT", "http://localhost:4317")


class TenantSpanProcessor(SpanProcessor):
    """Stamps tenant.id onto every span at start time."""

    def on_start(self, span, parent_context=None):
        span.set_attribute("tenant.id", TENTANT_ID)

    def on_end(self, span):
        pass

    def shutdown(self):
        pass

    def force_flush(self, timeout_millis=30000):
        return True


class TenantFormatter(logging.Formatter):
    """Adds tenant_id, host, and thread to every log record."""

    def format(self, record: logging.LogRecord) -> str:
        record.tenant_id = TENTANT_ID
        record.host = socket.gethostname()
        return super().format(record)


_LOG_FORMAT = (
    "%(asctime)s.%(msecs)03dZ "
    "[%(levelname)s] "
    "tenant=%(tenant_id)s "
    "host=%(host)s "
    "thread=%(thread)d "
    "%(name)s: %(message)s"
)

# --- Logs: Python logging → OTel Collector ---
_resource = Resource.create({
    "service.name": "litellm-demo",
    "tenant.id": TENTANT_ID,
    "host.name": socket.gethostname(),
})
_log_exporter = OTLPLogExporter(endpoint=OTEL_COLLECTOR_ENDPOINT)
_logger_provider = LoggerProvider(resource=_resource)
_logger_provider.add_log_record_processor(BatchLogRecordProcessor(_log_exporter))
set_logger_provider(_logger_provider)

_otel_handler = LoggingHandler(level=logging.DEBUG, logger_provider=_logger_provider)
_otel_handler.setFormatter(TenantFormatter(fmt=_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S"))

_console_handler = logging.StreamHandler()
_console_handler.setFormatter(TenantFormatter(fmt=_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S"))

logging.getLogger().handlers = []
logging.getLogger().addHandler(_otel_handler)
logging.getLogger().addHandler(_console_handler)
logging.getLogger().setLevel(logging.DEBUG)

# Must run BEFORE litellm imports the proxy app
TRACELOOP_BASE_URL = os.environ["TRACELOOP_BASE_URL"]

Traceloop.init(
    app_name="litellm-demo",
    api_endpoint=TRACELOOP_BASE_URL,
    api_key="KEY",
    disable_batch=True,
    should_enrich_metrics=True,
    metrics_exporter=OTLPMetricExporter(endpoint=OTEL_COLLECTOR_ENDPOINT),
)

# Inject tenant.id into every span — must run after Traceloop.init() sets the TracerProvider
_tracer_provider = trace.get_tracer_provider()
if isinstance(_tracer_provider, SDKTracerProvider):
    _tracer_provider.add_span_processor(TenantSpanProcessor())

# Code → Collector → Dynatrace

app = FastAPI()
FastAPIInstrumentor.instrument_app(app)
litellm.success_callback = ["otel"]
litellm.failure_callback = ["otel"]

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None


@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    kwargs = {"model": request.model, "messages": messages}
    if request.max_tokens is not None:
        kwargs["max_tokens"] = request.max_tokens
    if request.temperature is not None:
        kwargs["temperature"] = request.temperature

    try:
        ## Get the current span
        ## Update  the span with the Token Cost attribute
        response = litellm.completion(**kwargs)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




