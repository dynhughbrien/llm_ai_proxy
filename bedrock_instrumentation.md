 # Traceloop + boto3: GenAI Span Attributes
 
 **Yes** — but with caveats.
 
 Traceloop's [OpenLLMetry](https://github.com/traceloop/openllmetry) includes
 `opentelemetry-instrumentation-bedrock`, which patches boto3 calls to **Amazon Bedrock**
 and automatically populates OpenTelemetry GenAI semantic convention attributes:
 
 | Attribute | Auto-filled? |
 |---|---|
 | `gen_ai.system` | ✅ (`aws.bedrock`) |
 | `gen_ai.request.model` | ✅ |
 | `gen_ai.request.max_tokens` | ✅ |
 | `gen_ai.request.temperature` | ✅ |
 | `gen_ai.usage.input_tokens` | ✅ |
 | `gen_ai.usage.output_tokens` | ✅ |
 | `gen_ai.response.finish_reasons` | ✅ |
 
 ## Setup
 
 ```python
 from traceloop.sdk import Traceloop
 Traceloop.init()  # auto-detects and instruments boto3/bedrock
 ` `` 
 
 ## Caveats
 
 - Only works for **Bedrock** calls (`bedrock-runtime`), not generic boto3 services
 - Streaming responses may have limited attribute coverage depending on the version
 - Converse API is better supported than raw `invoke_model` in newer versions
