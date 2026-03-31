

# AWS Bedrock Guardrails: Complete Session Transcript

**Date:** March 31, 2026
**Topic:** AWS Bedrock Guardrails Options, Python Integration, and Observability Metrics
**User:** Hugh Brien (Lead Solutions Engineer at Dynatrace)

-----

## Table of Contents

1. [Overview: Guardrails Options](#overview-guardrails-options)
1. [Python Integration](#python-integration)
1. [Observability Metrics](#observability-metrics)
1. [Integration with LLM Observability Infrastructure](#integration-with-llm-observability-infrastructure)

-----

## Overview: Guardrails Options

### Question

What are the options with AWS Bedrock for guardrails?

### Answer

#### Core Filter/Policy Options

**Content Filters**
Detect and filter harmful text or image content in input prompts or model responses based on predefined categories:

- Hate
- Insults
- Sexual
- Violence
- Misconduct
- Prompt Attack

You can configure filter strength for each category based on your use case.

**Denied Topics**
Define a set of topics that are undesirable in your application context and block them in both user inputs and model responses (up to 30 denied topics).

**Word Filters**
Remove a specific list of words and phrases from conversations (exact match filtering). This filter is free to use.

**Sensitive Information Filters**
Remove PII (Personally Identifiable Information) from conversations for privacy protection.

**Contextual Grounding Check**
Filter hallucinations in responses to improve factual accuracy.

**Automated Reasoning Checks**
Use formal logic to help prevent factual errors from hallucinations. This is the first and only generative AI safeguard to use formal logic, validating correct model responses with up to 99% accuracy for mathematically verifiable explanations. Especially important in regulated industries.

#### Integration & Deployment

Guardrails can be used with any text or image foundation model by referencing the guardrail during model inference. They can be used with:

- Bedrock foundation models directly
- Bedrock Agents
- Bedrock Knowledge Bases

**Cross-Platform Support**
The ApplyGuardrail API allows you to use guardrails with any foundation model whether hosted on Amazon Bedrock or self-hosted models, including third-party models such as:

- OpenAI
- Google Gemini
- Any other external model

#### Pricing Consideration

Charges for guardrails are incurred only for the policies configured in the guardrail, with pricing varying by policy type:

- Content filters, denied topics, and PII policies are charged per 1,000 text units (each text unit contains up to 1,000 characters)
- Word filters are free
- Charges only apply when guardrails are actually invoked

#### Advanced Features

**Image Support** (Preview)
New image column in harmful categories supports certain models’ multimodal capabilities, currently in preview.

**Guardrail Profiles**
System-defined guardrail profiles define the destination AWS Regions where guardrail inference requests can be automatically routed to maintain performance and reliability.

-----

## Python Integration

### Question

What about if I’m running Python?

### Answer

#### Python SDK Integration

Use the **boto3** library (AWS SDK for Python) to interact with Bedrock Guardrails.

#### Approach 1: Direct Model Invocation with Guardrails

```python
import boto3
import json

client = boto3.client('bedrock-runtime', region_name='us-east-1')

response = client.invoke_model(
modelId='anthropic.claude-3-sonnet-20240229-v1:0',
body=json.dumps({
"messages": [{"role": "user", "content": "Your prompt here"}],
"max_tokens": 1024
}),
guardrailIdentifier='guardrail-id-here',
guardrailVersion='1'
)
```

#### Approach 2: Converse API (Recommended)

The newer `converse` and `converseStream` operations also support guardrails:

```python
response = client.converse(
modelId='anthropic.claude-3-sonnet-20240229-v1:0',
messages=[{"role": "user", "content": "Your prompt"}],
guardrailConfig={
'guardrailIdentifier': 'guardrail-id',
'guardrailVersion': '1'
}
)
```

#### Approach 3: ApplyGuardrail API (Standalone)

The ApplyGuardrail API allows you to assess content using preconfigured guardrails without invoking foundation models, enabling real-time content moderation.

```python
response = client.apply_guardrail(
guardrailIdentifier='guardrail-id',
guardrailVersion='1',
content=[{
'text': {'text': 'Your text to evaluate'}
}]
)
```

#### Python Frameworks for LLM Development

Given an interest in LLM observability, consider:

- **LangChain** – Integrates with Bedrock and supports guardrails configuration
- **Strands Agents** – Python framework for building AI agents with Bedrock, compatible with guardrails
- **LiteLLM** – Route Bedrock calls through your gateway with guardrails applied upstream

#### Example with Error Handling

```python
import json
import boto3
from botocore.exceptions import ClientError

class BedrockGuardrailsClient:
def __init__(self, guardrail_id, guardrail_version):
self.client = boto3.client('bedrock-runtime')
self.guardrail_id = guardrail_id
self.guardrail_version = guardrail_version

def invoke_with_guardrails(self, prompt):
try:
response = self.client.converse(
modelId='anthropic.claude-3-sonnet-20240229-v1:0',
messages=[{"role": "user", "content": prompt}],
guardrailConfig={
'guardrailIdentifier': self.guardrail_id,
'guardrailVersion': self.guardrail_version
}
)
return response['output']['message']['content'][0]['text']
except ClientError as e:
if e.response['Error']['Code'] == 'GuardContentPolicy':
# Handle guardrail violation
return "Content blocked by guardrail"
raise
```

#### Guardrail Error Handling

Common error codes to handle:

- `GuardContentPolicy` – Content violates configured content filters
- `GuardDeniedTopic` – Content matches denied topics
- `GuardWordPolicy` – Content contains blocked words
- `GuardSensitiveInformationPolicy` – PII detected and redacted

-----

## Observability Metrics

### Question

What observability metrics are published based upon guardrail usage?

### Answer

#### CloudWatch Metrics for Guardrails

Metrics are published to the CloudWatch namespace: **`AWS/Bedrock/Guardrails`**

#### Core Metrics

|Metric |Description |Use Case |
|--------------------------|-----------------------------------------------------------------------------|-------------------------------------|
|**Invocations** |Total number of guardrail evaluations |Track guardrail usage volume |
|**InvocationLatency** |Time taken to evaluate content |Performance monitoring; SLA tracking |
|**InvocationClientErrors**|Client-side errors during evaluation |Debug client issues |
|**InvocationServerErrors**|Server-side errors during evaluation |Monitor service health |
|**InvocationThrottles** |Rate limit violations |Capacity planning |
|**InvocationsIntervened** |Number of invocations where guardrails took action and blocked/masked content|Safety and policy violation tracking |
|**TextUnitCount** |Text units evaluated (each unit = up to 1,000 characters) |Cost calculation and billing tracking|

#### What “InvocationsIntervened” Tells You

This is the critical metric for safety monitoring. It tracks whenever a guardrail actually blocked or masked content. This directly correlates with:

- Harmful content detection attempts
- Prompt injection/jailbreak attempts
- PII that was redacted
- Policy violations by category
- Denied topic matches

#### Cost-Related Metrics

**TextUnitCount** is important because different policy types may have different pricing per cost unit:

- Content filters, denied topics, and PII: charged per 1,000 text units
- Word filters: free
- Automated Reasoning checks: separate pricing

Tracking this metric helps you monitor both guardrail effectiveness and guardrail spend.

#### Integration with Third-Party Observability Platforms

**Elastic Integration**
Elastic’s Bedrock integration now includes Guardrails monitoring. The integration tracks:

- Guardrail invocation count
- Invocation latency
- Text unit utilization
- Guardrail policy types associated with interventions
- Pre-built dashboards for visualization

#### Python Code to Access These Metrics

```python
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch')

# Fetch guardrail intervention metrics
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
'Value': 'your-guardrail-id'
}
]
)

print("Intervention Count:", response['Datapoints'])

# Also track invocation latency
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
'Value': 'your-guardrail-id'
}
]
)

print("Latency Metrics:", latency_response['Datapoints'])

# Track text unit consumption for cost tracking
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
'Value': 'your-guardrail-id'
}
]
)

print("Text Units Evaluated:", text_unit_response['Datapoints'])
```

#### Key Use Cases for Observability

**Security**

- Review and detect unusual jailbreak attempts
- Track sensitive information retrieval attempts
- Alert when intervention rates spike unexpectedly

**Compliance and Audit**

- Demonstrate policy enforcement for regulatory requirements
- Maintain audit trails of guardrail decisions
- Track which policies are triggered most frequently

**Guardrail Quality**

- Verify that your guardrail is working correctly
- Identify why unwanted behavior occurs without detection
- Tune filter thresholds based on intervention patterns

**Cost Optimization**

- Monitor TextUnitCount to track guardrail costs
- Identify which policies consume the most units
- Optimize policy configurations to reduce cost

-----

## Integration with LLM Observability Infrastructure

### Recommended Architecture for Enterprise LLM Observability

For your existing setup with:

- Traceloop/OpenLLMetry auto-instrumentation
- LiteLLM as LLM gateway
- FastAPI services
- Dynatrace for OTLP ingestion
- OpenTelemetry token cost tracking

#### Integration Strategy

1. **Parallel Metric Collection**
Poll CloudWatch metrics alongside your OTLP traces
1. **Correlation with Traces**
Correlate `InvocationsIntervened` spikes with specific prompts/traces in Dynatrace using trace IDs and timestamps
1. **Cost Attribution**
Track guardrail cost as a separate dimension in your token cost tracking (alongside model tokens, cache tokens, etc.)
1. **Alerting Strategy**
- Alert on intervention rate increases (potential security issue)
- Alert on latency degradation (performance issue)
- Alert on text unit consumption trends (cost optimization)

#### Example: Unified Observability Client

```python
import boto3
from datetime import datetime, timedelta
from opentelemetry import metrics

class BedrockObservabilityClient:
def __init__(self, guardrail_id, guardrail_version):
self.cloudwatch = boto3.client('cloudwatch')
self.guardrail_id = guardrail_id
self.guardrail_version = guardrail_version
self.meter = metrics.get_meter(__name__)

# Create OTel metrics
self.intervention_counter = self.meter.create_counter(
"bedrock.guardrails.interventions",
description="Number of guardrail interventions"
)
self.latency_histogram = self.meter.create_histogram(
"bedrock.guardrails.latency_ms",
description="Guardrail evaluation latency"
)
self.text_units_counter = self.meter.create_counter(
"bedrock.guardrails.text_units",
description="Text units evaluated"
)

def get_intervention_metrics(self, hours=1):
"""Fetch intervention metrics from CloudWatch and record to OTel"""
response = self.cloudwatch.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationsIntervened',
StartTime=datetime.now() - timedelta(hours=hours),
EndTime=datetime.now(),
Period=300,
Statistics=['Sum'],
Dimensions=[{'Name': 'GuardrailId', 'Value': self.guardrail_id}]
)

# Record to OTel
for datapoint in response['Datapoints']:
self.intervention_counter.add(
datapoint['Sum'],
attributes={
'guardrail_id': self.guardrail_id,
'timestamp': datapoint['Timestamp'].isoformat()
}
)

return response

def get_latency_metrics(self, hours=1):
"""Fetch latency metrics from CloudWatch and record to OTel"""
response = self.cloudwatch.get_metric_statistics(
Namespace='AWS/Bedrock/Guardrails',
MetricName='InvocationLatency',
StartTime=datetime.now() - timedelta(hours=hours),
EndTime=datetime.now(),
Period=300,
Statistics=['Average', 'Maximum'],
Dimensions=[{'Name': 'GuardrailId', 'Value': self.guardrail_id}]
)

# Record to OTel
for datapoint in response['Datapoints']:
self.latency_histogram.record(
datapoint.get('Average', 0),
attributes={
'guardrail_id': self.guardrail_id,
'statistic': 'average'
}
)
self.latency_histogram.record(
datapoint.get('Maximum', 0),
attributes={
'guardrail_id': self.guardrail_id,
'statistic': 'maximum'
}
)

return response
```

This gives you a complete observability picture:

- **Model performance** via token counts and latency
- **Guardrail effectiveness** via intervention rates
- **Policy violations** via intervention categories
- **Cost attribution** via text unit consumption

-----

## Summary

AWS Bedrock Guardrails provides comprehensive safety controls with six main policy types (content filters, denied topics, word filters, sensitive information, contextual grounding, and automated reasoning). Python integration is straightforward via boto3 with three main approaches: direct model invocation, Converse API, or standalone ApplyGuardrail API.

Observability is native to CloudWatch with key metrics including invocations, latency, errors, throttles, interventions, and text unit consumption. For enterprise LLM observability stacks, guardrails metrics should be correlated with OTLP traces and token cost tracking to provide comprehensive visibility into both model performance and safety enforcement.

-----

**End of Session**
