# Traceloop, Boto3, and AWS Bedrock Guardrails Instrumentation

**Date:** March 31, 2026
**Topic:** Does Traceloop Instrument boto3? Complete Setup Guide
**User:** Hugh Brien (Lead Solutions Engineer at Dynatrace)

-----

## Table of Contents

1. [Overview: Traceloop and boto3](#overview-traceloop-and-boto3)
1. [OpenTelemetry botocore Instrumentation](#opentelemetry-botocore-instrumentation)
1. [Setup for Bedrock Guardrails](#setup-for-bedrock-guardrails)
1. [Complete Stack Integration](#complete-stack-integration)
1. [What Gets Traced](#what-gets-traced)
1. [Troubleshooting and Best Practices](#troubleshooting-and-best-practices)

-----

## Overview: Traceloop and boto3

### Question

Does Traceloop instrument the boto3 AWS Python library?

### Answer

The answer is **yes, but with an important nuance**.

#### Traceloop Native boto3 Support

Traceloop’s SDK provides **native instrumentation for Bedrock LLM calls via boto3**. Traceloop’s SDK will automatically log all calls to Bedrock using boto3—both prompts and completions.

This is LLM-specific instrumentation that Traceloop provides out-of-the-box for foundation model interactions.

#### For General boto3 AWS Calls

For broader AWS SDK instrumentation beyond just LLM calls—such as CloudWatch metrics collection, S3, DynamoDB, Lambda, and **importantly, Bedrock Guardrails API calls**—Traceloop does not directly instrument boto3.

Instead, you use **OpenTelemetry’s standard botocore instrumentation**, which is the underlying library that powers boto3.

### Why This Architecture?

The separation of concerns makes sense:

- **Traceloop/OpenLLMetry**: Captures LLM-specific semantics (prompts, completions, token counts, model IDs)
- **OpenTelemetry botocore**: Captures infrastructure-level AWS API calls, latency, errors, and metadata

You can use both simultaneously in the same application.

-----

## OpenTelemetry botocore Instrumentation

### Key Architecture Detail

Python’s AWS SDK is built in two layers: botocore (the low-level client) and boto3 (the high-level resource abstraction). The OpenTelemetry instrumentation targets botocore, which means it catches calls from both boto3 and botocore.

This is important: **one instrumentation covers all boto3 calls** because boto3 is just a wrapper around botocore.

### Installation

```bash
# Core OpenTelemetry packages
pip install opentelemetry-api opentelemetry-sdk

# OTLP exporter (for sending to Dynatrace, Jaeger, etc.)
pip install opentelemetry-exporter-otlp-proto-grpc

# boto3/botocore instrumentation
pip install opentelemetry-instrumentation-botocore
```

### Basic Setup

```python
import boto3
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

# Configure OpenTelemetry resource with service context
resource = Resource(attributes={
SERVICE_NAME: "bedrock-guardrails-service",
"cloud.provider": "aws",
})

# Create tracer provider with OTLP exporter
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
endpoint="http://localhost:4317", # Your OTLP endpoint
insecure=True
)
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Instrument all boto3/botocore calls
BotocoreInstrumentor().instrument()

# Now all boto3 calls are automatically traced
client = boto3.client('s3', region_name='us-east-1')

# This S3 call will automatically create a span
response = client.put_object(
Bucket='my-bucket',
Key='my-key',
Body=b'data'
)
```

-----

## Setup for Bedrock Guardrails

### Python Code Example

```python
import boto3
import json
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

# Initialize OpenTelemetry
resource = Resource(attributes={
SERVICE_NAME: "bedrock-guardrails-service",
"cloud.provider": "aws",
"service.version": "1.0.0",
})
provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
endpoint="http://localhost:4317", # Dynatrace OTLP endpoint
insecure=True
)
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Instrument boto3
BotocoreInstrumentor().instrument()

# Create Bedrock client
client = boto3.client('bedrock-runtime', region_name='us-east-1')

# Invoke model with guardrails
# This will create spans for:
# 1. The boto3 converse API call
# 2. Guardrail evaluation
# 3. Model invocation
response = client.converse(
modelId='anthropic.claude-3-sonnet-20240229-v1:0',
messages=[{"role": "user", "content": "Your prompt here"}],
guardrailConfig={
'guardrailIdentifier': 'my-guardrail-id',
'guardrailVersion': '1'
}
)

print("Response:", response['output']['message']['content'][0]['text'])
```

### Standalone Guardrail Evaluation

For evaluating content without model invocation:

```python
import boto3
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

BotocoreInstrumentor().instrument()

client = boto3.client('bedrock-runtime', region_name='us-east-1')

# This apply_guardrail call will be traced
response = client.apply_guardrail(
guardrailIdentifier='my-guardrail-id',
guardrailVersion='1',
content=[{
'text': {'text': 'Content to evaluate'}
}]
)

# Response includes:
# - assessments: Policy violations detected
# - invocationLatency: Time taken for evaluation
# - usage: TextUnitCount for billing
print("Guardrail Response:", response)
```

### Fetching Guardrail Metrics from CloudWatch

```python
import boto3
from datetime import datetime, timedelta
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

# Instrument boto3 for CloudWatch calls too
BotocoreInstrumentor().instrument()

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Fetch intervention metrics - these calls are also traced
response = cloudwatch.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationsIntervened',
StartTime=datetime.now() - timedelta(hours=1),
EndTime=datetime.now(),
Period=300, # 5-minute intervals
Statistics=['Sum', 'Average'],
Dimensions=[
{
'Name': 'GuardrailId',
'Value': 'my-guardrail-id'
}
]
)

print("Intervention Count:", response['Datapoints'])

# Fetch latency metrics
latency_response = cloudwatch.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationLatency',
StartTime=datetime.now() - timedelta(hours=1),
EndTime=datetime.now(),
Period=300,
Statistics=['Average', 'Maximum'],
Dimensions=[
{
'Name': 'GuardrailId',
'Value': 'my-guardrail-id'
}
]
)

print("Latency Metrics:", latency_response['Datapoints'])

# Fetch text unit consumption for cost tracking
text_unit_response = cloudwatch.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='TextUnitCount',
StartTime=datetime.now() - timedelta(hours=1),
EndTime=datetime.now(),
Period=300,
Statistics=['Sum'],
Dimensions=[
{
'Name': 'GuardrailId',
'Value': 'my-guardrail-id'
}
]
)

print("Text Units Evaluated:", text_unit_response['Datapoints'])
```

-----

## Complete Stack Integration

### Full FastAPI + Traceloop + Botocore Example

This example shows a production-ready setup combining:

- **Traceloop**: LLM observability (prompts, completions, tokens)
- **BotocoreInstrumentor**: AWS infrastructure observability (guardrails, CloudWatch, metrics)
- **FastAPI instrumentation**: HTTP layer observability

```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
boto3==1.28.0
traceloop-sdk==0.1.0
opentelemetry-api==1.20.0
opentelemetry-sdk==1.20.0
opentelemetry-exporter-otlp-proto-grpc==0.41b0
opentelemetry-instrumentation-fastapi==0.41b0
opentelemetry-instrumentation-botocore==0.41b0
```

```python
# main.py - FastAPI application with integrated observability

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
from traceloop.sdk import Traceloop
import boto3
import json

# Initialize Traceloop for LLM-specific observability
Traceloop.init(
app_name="bedrock-guardrails-service",
# Additional Traceloop config can go here
)

# Configure base OTLP tracer for infrastructure observability
resource = Resource(attributes={
SERVICE_NAME: "bedrock-guardrails-service",
"cloud.provider": "aws",
"deployment.environment": "production",
})

provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(
endpoint="http://dynatrace-collector:4317", # Your Dynatrace OTLP endpoint
insecure=True
)
processor = BatchSpanProcessor(otlp_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Instrument HTTP and AWS layers
app = FastAPI(title="Bedrock Guardrails Service")
FastAPIInstrumentor().instrument_app(app)
BotocoreInstrumentor().instrument()

# Get tracer for custom spans
tracer = trace.get_tracer(__name__)

# Bedrock client
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
cloudwatch_client = boto3.client('cloudwatch', region_name='us-east-1')

class ChatRequest(BaseModel):
prompt: str
guardrail_id: str
guardrail_version: str = "1"

class ChatResponse(BaseModel):
response: str
guardrail_intervened: bool
intervention_reason: str = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
"""
Chat endpoint with guardrail protection.

Observability:
- Traceloop traces: LLM invocation, prompt, completion, tokens
- BotocoreInstrumentor traces: AWS API calls (converse, guardrail evaluation)
- Custom spans: Business logic and error handling
"""

with tracer.start_as_current_span("chat_request") as span:
span.set_attribute("guardrail.id", request.guardrail_id)
span.set_attribute("request.type", "chat_with_guardrails")

try:
# This converse call will be traced by both Traceloop and BotocoreInstrumentor
with tracer.start_as_current_span("bedrock_converse"):
response = bedrock_client.converse(
modelId='anthropic.claude-3-sonnet-20240229-v1:0',
messages=[{"role": "user", "content": request.prompt}],
guardrailConfig={
'guardrailIdentifier': request.guardrail_id,
'guardrailVersion': request.guardrail_version
}
)

# Extract response
output_text = response['output']['message']['content'][0]['text']

# Track if guardrail intervened
guardrail_intervened = response.get('guardrailAction') == 'INTERVENED'
intervention_reason = None

if guardrail_intervened:
span.set_attribute("guardrail.intervened", True)
# Get the actual intervention reason from response
assessments = response.get('assessments', [])
if assessments:
intervention_reason = str(assessments[0])

return ChatResponse(
response=output_text,
guardrail_intervened=guardrail_intervened,
intervention_reason=intervention_reason
)

except Exception as e:
span.record_exception(e)
span.set_attribute("error.type", type(e).__name__)
raise HTTPException(status_code=500, detail=str(e))

@app.get("/guardrail-metrics/{guardrail_id}")
async def get_guardrail_metrics(guardrail_id: str, hours: int = 1):
"""
Fetch guardrail metrics from CloudWatch.

This endpoint demonstrates using botocore instrumentation
to trace CloudWatch API calls.
"""
from datetime import datetime, timedelta

with tracer.start_as_current_span("fetch_guardrail_metrics") as span:
span.set_attribute("guardrail.id", guardrail_id)
span.set_attribute("time_range_hours", hours)

try:
# CloudWatch calls are also traced by BotocoreInstrumentor
with tracer.start_as_current_span("cloudwatch_interventions"):
intervention_response = cloudwatch_client.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationsIntervened',
StartTime=datetime.now() - timedelta(hours=hours),
EndTime=datetime.now(),
Period=300,
Statistics=['Sum'],
Dimensions=[{'Name': 'GuardrailId', 'Value': guardrail_id}]
)

with tracer.start_as_current_span("cloudwatch_latency"):
latency_response = cloudwatch_client.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationLatency',
StartTime=datetime.now() - timedelta(hours=hours),
EndTime=datetime.now(),
Period=300,
Statistics=['Average', 'Maximum'],
Dimensions=[{'Name': 'GuardrailId', 'Value': guardrail_id}]
)

with tracer.start_as_current_span("cloudwatch_text_units"):
text_units_response = cloudwatch_client.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='TextUnitCount',
StartTime=datetime.now() - timedelta(hours=hours),
EndTime=datetime.now(),
Period=300,
Statistics=['Sum'],
Dimensions=[{'Name': 'GuardrailId', 'Value': guardrail_id}]
)

return {
"guardrail_id": guardrail_id,
"interventions": intervention_response['Datapoints'],
"latency": latency_response['Datapoints'],
"text_units": text_units_response['Datapoints'],
}

except Exception as e:
span.record_exception(e)
raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
"""Health check endpoint"""
return {"status": "healthy"}

if __name__ == "__main__":
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1

# Run the service
python main.py
```

### Testing with curl

```bash
# Chat with guardrails
curl -X POST http://localhost:8000/chat \
-H "Content-Type: application/json" \
-d '{
"prompt": "Hello, how are you?",
"guardrail_id": "my-guardrail-id"
}'

# Fetch guardrail metrics
curl http://localhost:8000/guardrail-metrics/my-guardrail-id?hours=1

# Health check
curl http://localhost:8000/health
```

-----

## What Gets Traced

### From Traceloop/OpenLLMetry

When you use Traceloop with Bedrock:

- **LLM Model Invocation** – Model ID, start/end times
- **Prompt Data** – Full input prompt
- **Completion Data** – Model’s output
- **Token Usage** – Input tokens, output tokens, total
- **Model-specific Metadata** – Temperature, max_tokens, etc.

**Important**: Traceloop captures the **semantic meaning** of the LLM interaction.

### From BotocoreInstrumentor (OpenTelemetry)

When you instrument with `BotocoreInstrumentor()`:

- **AWS Service Name** – e.g., “bedrock-runtime”, “cloudwatch”
- **Operation Name** – e.g., “Converse”, “GetMetricStatistics”, “ApplyGuardrail”
- **Request/Response Details** – Service-specific metadata
- **Latency** – Time taken for the API call
- **Error Status** – HTTP status codes, error messages
- **AWS Metadata**
- `aws.region` – AWS region
- `aws.request_id` – Unique AWS request identifier
- `aws.service` – Service name

### Key Span Attributes for Guardrails

When instrumented, each AWS call produces spans with useful attributes:

- `rpc.service` – The AWS service (e.g., “bedrock-runtime”)
- `rpc.method` – The operation (e.g., “Converse”, “ApplyGuardrail”)
- `aws.region` – Region where the call was made
- `http.status_code` – Response status
- `aws.request_id` – AWS request ID for correlation

Example span hierarchy for a guardrailed chat:

```
Span: POST /chat (FastAPI)
├─ Span: chat_request (custom business logic)
│ ├─ Span: bedrock_converse (BotocoreInstrumentor)
│ │ ├─ Attributes:
│ │ │ - rpc.service: bedrock-runtime
│ │ │ - rpc.method: Converse
│ │ │ - aws.region: us-east-1
│ │ │ - aws.request_id: abc-123-def
│ │ │ - http.status_code: 200
│ │ │ - duration_ms: 1245
│ │ └─ Traceloop: LLM data (prompt, completion, tokens)
│ └─ Error handling (if any)
```

-----

## Troubleshooting and Best Practices

### Ensure Tracer is Set Before Creating Clients

```python
# CORRECT - Set tracer provider BEFORE creating clients
trace.set_tracer_provider(provider)
BotocoreInstrumentor().instrument() # Instrument AFTER setting provider
client = boto3.client('bedrock-runtime') # Create client AFTER instrumentation

# INCORRECT - This won't work
client = boto3.client('bedrock-runtime')
BotocoreInstrumentor().instrument() # Too late - client already created
```

### Disable Batch Processing for Local Development

```python
# For local testing, use SimpleSpanProcessor instead of BatchSpanProcessor
# so you see traces immediately without waiting for batch flush
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

provider = TracerProvider(resource=resource)
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
provider.add_span_processor(SimpleSpanProcessor(otlp_exporter)) # Immediate export
```

### Combining Traceloop with Botocore in Same Application

```python
# Initialize Traceloop FIRST
Traceloop.init(app_name="my-service")

# Then set up OpenTelemetry for infrastructure
# ... rest of OTel setup ...

# Instrument both
BotocoreInstrumentor().instrument()
FastAPIInstrumentor().instrument_app(app)

# Both will contribute spans to the same trace context
```

### Filtering Sensitive Data

If you need to redact sensitive data from spans (like guardrail-blocked prompts):

```python
from opentelemetry.sdk.trace.export import SpanProcessor

class RedactingSpanProcessor(SpanProcessor):
def on_end(self, span):
# Redact sensitive attributes before export
if "bedrock" in span.name.lower():
if span.attributes and "prompt" in span.attributes:
span.attributes["prompt"] = "[REDACTED]"

provider = TracerProvider(resource=resource)
provider.add_span_processor(RedactingSpanProcessor())
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
```

### Monitor Span Creation Overhead

BotocoreInstrumentor adds minimal overhead (typically <5ms per call), but for high-throughput applications:

```python
# Use sampling to reduce trace volume
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

sampler = TraceIdRatioBased(0.1) # Sample 10% of traces
provider = TracerProvider(resource=resource, sampler=sampler)
```

### Dynatrace-Specific Configuration

If you’re sending to Dynatrace OTLP endpoint:

```python
otlp_exporter = OTLPSpanExporter(
endpoint="https://your-environment.live.dynatrace.com/api/v2/otlp",
headers=(("Authorization", "Api-Token YOUR_TOKEN"),),
# Don't use insecure=True in production
)
```

-----

## Summary

**Does Traceloop instrument boto3?**

- **Yes for LLM calls**: Traceloop natively instruments Bedrock via boto3
- **Not directly for all AWS calls**: Use OpenTelemetry’s `BotocoreInstrumentor` for general AWS SDK tracing

**For guardrails specifically:**

1. Use Traceloop for the LLM layer (prompts, completions, tokens)
1. Use `BotocoreInstrumentor` for the infrastructure layer (guardrail evaluations, CloudWatch metrics)
1. Both export to the same OTLP endpoint (e.g., Dynatrace)
1. This gives you complete visibility from LLM semantics down to AWS infrastructure latency

**Installation:**

```bash
pip install opentelemetry-instrumentation-botocore opentelemetry-exporter-otlp-proto-grpc
```

**Setup:**

```python
from opentelemetry.instrumentation.botocore import BotocoreInstrumentor
BotocoreInstrumentor().instrument()
```

That’s it. All subsequent boto3 calls are automatically traced.

-----

**End of Session**
