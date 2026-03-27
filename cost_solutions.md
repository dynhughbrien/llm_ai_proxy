# OpenTelemetry Lookup Processor & LiteLLM Token Cost Tracking

## Part 1: OpenTelemetry Lookup Processor for Span Enrichment

### Overview

The OpenTelemetry Lookup Processor enriches telemetry data by matching attribute values against external reference sources and adding corresponding metadata. This is the purpose-built component for inserting fields into spans based on lookup table values.

### Your Use Case: LLM Model → Token Cost

The Lookup Processor allows you to automatically enrich spans with business context like token costs based on model names.

#### Configuration Example

```yaml
processors:
  lookup:
    tables:
      model_costs:
        "gpt-4": cost_per_token: 0.00003
        "gpt-3.5-turbo": cost_per_token: 0.0000015
        "claude-3-opus": cost_per_token: 0.000015
    lookups:
      - attribute: gen_ai.model
        table: model_costs
        default:
          cost_per_token: "unknown"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [lookup, batch]
      exporters: [otlp]
```

When a span comes through with `gen_ai.model="gpt-4"`, the collector automatically adds `cost_per_token: 0.00003` to the span attributes.

### Advanced Features

#### External CSV Files for Dynamic Pricing

The Lookup processor supports loading external CSV files for larger datasets, allowing lookup data to be updated without restarting the collector via configurable reload intervals. Perfect if your pricing tables change frequently.

#### Default Values and Match Flags

You can set default values when no match is found and optionally add a flag indicating whether the lookup succeeded:

```yaml
processors:
  lookup:
    tables:
      model_costs:
        "gpt-4": cost_per_token: 0.00003
    lookups:
      - attribute: gen_ai.model
        table: model_costs
        default:
          cost_per_token: "unknown"
          lookup_available: false
        add_match_flag: true
        match_flag_attribute: lookup.matched
```

### Alternative: The Transform Processor

If the lookup is complex or context-dependent, you can use the transform processor with OTTL (OpenTelemetry Transform Language) to set attributes conditionally. However, for simple table lookups, the Lookup Processor is cleaner and more performant.

### Integration with Spring Boot

For your Spring Boot setup, you'd deploy the Lookup Processor in the collector that receives OTLP from your Spring app. Since you're already instrumenting with OTel, this is a clean separation of concerns: your app sends raw data, and the collector enriches it with business context (like token costs).

---

## Part 2: LiteLLM Token Cost Computation

### When Token Cost is Enabled

By default, LiteLLM returns token usage in all completion requests and exposes three public helper functions: `token_counter`, `cost_per_token`, and `completion_cost`. **Cost tracking is enabled by default** — you don't need to opt in.

### How Token Cost is Computed

The `completion_cost` function combines `token_counter` and `cost_per_token` to return the overall cost (in USD) for a given LLM API call, counting both input and output token costs.

#### The Process

1. **Token Counting**
   - LiteLLM uses model-specific tokenizers for Anthropic, Cohere, Llama2, and OpenAI
   - Defaults to tiktoken if no model-specific tokenizer is available

2. **Pricing Lookup**
   - LiteLLM maintains a centralized pricing database (`model_prices_and_context_window.json`)
   - Contains input and output cost-per-token for hundreds of models across all supported providers
   - Live list available at api.litellm.ai

3. **Cost Calculation**
   - After each request completes, the cost is automatically calculated
   - Attached to the response object in `response._hidden_params["response_cost"]`
   - Logged for spend tracking

### Example Code

```python
from litellm import completion

response = completion(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hey, how's it going?"}]
)

# Cost is automatically calculated and available here:
cost = response._hidden_params["response_cost"]
print(f"Cost: ${cost}")
```

### Custom Pricing

You can override the default pricing for your own models by adding a `model_info` key to your model configuration with custom `input_cost_per_token` and `output_cost_per_token` values:

```yaml
model_list:
  - model_name: "prod/claude-3-5-sonnet"
    litellm_params:
      model: "anthropic/claude-3-5-sonnet-20241022"
    model_info:
      input_cost_per_token: 0.000006
      output_cost_per_token: 0.00003
```

### Advanced Features

LiteLLM supports:
- **Tiered pricing** for models with variable costs (e.g., Anthropic's > 200k token pricing, Bedrock service tiers)
- **Cache-specific costs** for prompt caching

### Helper Functions

LiteLLM also exposes standalone helper functions:

```python
from litellm import token_counter, cost_per_token

# Count tokens for a message
messages = [{"role": "user", "content": "Hey, how's it going"}]
token_count = token_counter(model="gpt-3.5-turbo", messages=messages)

# Get cost per token
prompt_tokens = 5
completion_tokens = 10
prompt_cost, completion_cost = cost_per_token(
    model="gpt-3.5-turbo",
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens
)
print(f"Prompt cost: ${prompt_cost}, Completion cost: ${completion_cost}")
```

---

## Integration: LiteLLM + OpenTelemetry Lookup Processor

### Recommended Architecture

1. **LiteLLM calculates cost** in your application (either Python SDK or via the LiteLLM Proxy)
2. **Add cost to span** as an attribute during instrumentation
3. **OpenTelemetry Lookup Processor** validates or enriches the cost attribute based on your lookup table
4. **Collector exports** enriched span to your observability backend

### Example: Python App with OTel

```python
from litellm import completion
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def call_llm(model: str, messages: list):
    with tracer.start_as_current_span("llm_call") as span:
        # Make the LLM call
        response = completion(
            model=model,
            messages=messages
        )
        
        # LiteLLM automatically calculated cost
        cost = response._hidden_params["response_cost"]
        usage = response.usage
        
        # Add to span attributes
        span.set_attribute("gen_ai.model", model)
        span.set_attribute("gen_ai.request.token.count", usage.prompt_tokens)
        span.set_attribute("gen_ai.response.token.count", usage.completion_tokens)
        span.set_attribute("litellm.cost.usd", cost)
        
        return response
```

The Lookup Processor then can:
- Validate the cost matches your pricing table
- Flag any pricing mismatches
- Add additional cost breakdowns (e.g., cache cost, reasoning token cost)

---

## Summary

- **LiteLLM**: Automatically computes token costs after each API call; cost available in `response._hidden_params["response_cost"]`
- **OpenTelemetry Lookup Processor**: Enriches spans with business context (like per-model pricing) based on lookup tables
- **Together**: LiteLLM provides the raw cost, OTel Lookup Processor validates/enriches it for observability and compliance
