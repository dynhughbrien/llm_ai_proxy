
Traceloop & AWS Bedrock GenAI Span Attributes
✅ Final, verified answer (corrected and source‑aligned)
Does Traceloop correctly process AWS Bedrock responses and populate gen_ai.* span attributes?
Yes — but only under specific, well‑defined conditions.
Traceloop does correctly populate OpenTelemetry GenAI semantic attributes (gen_ai.*) for AWS Bedrock when:

The Bedrock call is made via a supported API (Converse preferred)
The model provider is supported
The request is made through boto3 bedrock-runtime with Traceloop / OpenLLMetry enabled
This behavior is not universal across all Bedrock models or APIs and varies by API and provider.


What Traceloop is actually doing
Traceloop does not parse Bedrock responses itself. It relies on:

OpenLLMetry
OpenTelemetry Bedrock / botocore instrumentation
These libraries:

Intercept boto3 bedrock-runtime calls
Recognize specific Bedrock APIs
Extract model metadata, token usage, and (optionally) content
Emit spans using GenAI semantic conventions


✅ Converse / ConverseStream (fully supported — recommended)
The Converse and ConverseStream APIs:

Use a normalized request and response structure
Are explicitly supported by the Bedrock OpenTelemetry instrumentation
Emit spans, events, and metrics, including token usage
When using Converse, the following attributes are populated reliably:

gen_ai.system = aws.bedrock
gen_ai.request.model
gen_ai.request.* (temperature, max_tokens, etc.)
gen_ai.usage.*
gen_ai.response.finish_reasons
✅ Converse is the recommended path for GenAI observability.


⚠️ InvokeModel / InvokeModelWithResponseStream (limited support)
Support for InvokeModel is partial and provider‑dependent.
GenAI semantic extraction is implemented only for a subset of models, explicitly:

Amazon Titan
Amazon Nova
Anthropic Claude
Tool‑call extraction via InvokeModel is supported only for Nova and Claude 3+.
✅ Therefore:

Traceloop may populate gen_ai.* attributes for InvokeModel, but only when the model provider and response schema are explicitly supported.


❌ It is not guaranteed for all InvokeModel calls.


Why spans may exist without GenAI attributes
A common (and expected) scenario:

The boto3 call is traced ✅
A span exists ✅
gen_ai.* attributes are missing ❌
This occurs when:

The API / model combination is unsupported, or
The response payload structure cannot be parsed deterministically
This behavior is documented and expected, not a Traceloop bug.


Prompt & completion content capture

Prompt and completion content is disabled by default
To capture content, explicitly enable:
TRACELOOP_TRACE_CONTENT=true


This applies regardless of API.


✅ Final summary (safe to reuse)

Traceloop correctly processes AWS Bedrock responses and populates gen_ai.* span attributes when the Bedrock API and model provider are supported by the underlying OpenTelemetry Bedrock instrumentation.

Converse / ConverseStream: fully supported, reliable GenAI attributes
InvokeModel: partial support, limited to Titan, Nova, and Claude
Prompt/completion content requires explicit opt‑in
Missing attributes usually indicate an unsupported model or API


