# LiteLLM: Token Usage, Cost & Estimation

## 1. The Pricing Database — `model_prices_and_context_window.json`

This is the heart of LiteLLM's cost system — a centralized, community-maintained JSON file covering 100+ LLM providers. It maintains costs for all supported models, including special pricing like prompt caching, reasoning tokens, and provider-specific billing models.

**Every LLM you route traffic through must have a corresponding entry in this database.** This applies whether you are using a hosted provider (OpenAI, Anthropic, Google Vertex, AWS Bedrock, Azure, Cohere, etc.), a self-hosted model via Ollama or vLLM, or a custom fine-tuned deployment. Each entry acts as the single source of truth for that model's identity and economics — without it, LiteLLM cannot calculate cost, enforce budgets, or report spend.

Each entry captures three categories of information:

- **Identity** — the model name, provider (`litellm_provider`), mode (`chat`, `embedding`, `image_generation`, etc.), supported capabilities (function calling, tool choice, vision), and any dated aliases that map to the same model
- **Context window** — `max_input_tokens` and `max_output_tokens` define the hard limits LiteLLM uses for routing decisions and token budget checks
- **Cost** — `input_cost_per_token` and `output_cost_per_token` are the baseline per-token USD prices; additional cost fields cover tiered pricing (large contexts, cache reads/writes, reasoning tokens, audio, images, and batch/flex modes)

When you call any LLM through LiteLLM, the framework looks up the model key in this file, reads its cost fields, multiplies them against the actual token counts returned in the response's `usage` object, and records the total spend. If a model is missing from the file — or if you are using a private deployment with different pricing — you register a custom entry to override or supplement the defaults.

Each model entry in the spec looks like this:

```json
{
  "claude-sonnet-4-5": {
    "aliases": ["claude-sonnet-4-5-20250929"],
    "input_cost_per_token": 3e-06,
    "output_cost_per_token": 1.5e-05,
    "litellm_provider": "anthropic",
    "max_input_tokens": 200000,
    "max_output_tokens": 64000,
    "mode": "chat",
    "supports_function_calling": true,
    "supports_tool_choice": true
  }
}
```

At load time, each alias is expanded into a top-level entry sharing the same data as the canonical entry — making both `claude-sonnet-4-5` and `claude-sonnet-4-5-20250929` resolve with the same pricing and capabilities.

### Key Pricing Fields

| Field | Purpose |
|---|---|
| `input_cost_per_token` | Standard prompt token cost |
| `output_cost_per_token` | Standard completion token cost |
| `input_cost_per_token_above_200k_tokens` | Tiered pricing for large contexts |
| `output_cost_per_token_above_200k_tokens` | Tiered pricing for large contexts |
| `cache_creation_input_token_cost` | Prompt cache write cost |
| `cache_read_input_token_cost` | Prompt cache read cost (much cheaper) |
| `output_cost_per_reasoning_token` | For o1-style reasoning models |
| `input_cost_per_audio_token` | Audio/voice input |
| `input_cost_per_image` | Multimodal image input |
| `input_cost_per_token_flex` / `output_cost_per_token_flex` | Batch/flex tier pricing |
| `max_input_tokens` / `max_output_tokens` | Context window bounds |
| `deprecation_date` | When a model goes away |

---

## 2. Core Python SDK Functions

LiteLLM provides three main utilities:

- **`token_counter`** — returns the number of tokens for a given input using model-specific tokenizers, defaulting to tiktoken if none is available
- **`cost_per_token`** — returns cost in USD for prompt and completion tokens separately
- **`completion_cost`** — returns the overall USD cost for a full LLM API call, combining both of the above

```python
# Token counting
from litellm import token_counter
messages = [{"role": "user", "content": "Hey, how's it going"}]
token_count = token_counter(model="gpt-3.5-turbo", messages=messages)

# Cost per token (returns input_cost, output_cost as a tuple)
from litellm import cost_per_token
input_cost, output_cost = cost_per_token(
    model="gpt-3.5-turbo",
    prompt_tokens=5,
    completion_tokens=10
)

# Full completion cost (post-call)
from litellm import completion_cost
cost = completion_cost(
    model="gpt-3.5-turbo",
    prompt="Hey, how's it going",
    completion="Hi, I'm gpt - I am doing well"
)

# Cost is also embedded in every response
response = litellm.completion(model="gpt-3.5-turbo", messages=[...])
print(response._hidden_params["response_cost"])
```

---

## 3. Tokenizer Strategy

LiteLLM uses provider-specific tokenizers where available, with a character-based fallback estimating ~4 characters per token when no tokenizer is available.

| Provider | Tokenizer |
|---|---|
| OpenAI | tiktoken |
| Anthropic | Claude JSON tokenizer via `Tokenizer.from_str()` |
| HuggingFace | HF tokenizers library |
| Llama2 / Llama3, Cohere | Native tokenizers |
| Custom models | `create_pretrained_tokenizer()` or `create_tokenizer()` from JSON |

---

## 4. Multi-Tier Pricing (Provider-Aware)

For providers that support multiple pricing tiers, LiteLLM automatically applies the correct cost based on the response:

- **Vertex AI Gemini** — uses `usageMetadata.trafficType` (`ON_DEMAND_PRIORITY` → priority, `FLEX/BATCH` → flex)
- **Bedrock** — uses `serviceTier` from the response

For **free/on-prem models** (e.g., Ollama), explicitly zero out costs to bypass all budget checks:

```yaml
model_list:
  - model_name: on-prem-llama
    litellm_params:
      model: ollama/llama3
      api_base: http://localhost:11434
    model_info:
      input_cost_per_token: 0   # bypass all budget checks
      output_cost_per_token: 0
```

---

## 5. Proxy Spend Tracking

The LiteLLM proxy exposes full spend tracking APIs. The `/user/daily/activity` endpoint returns a breakdown by models, providers, and API keys:

```json
{
  "metrics": {
    "spend": 0.0177072,
    "prompt_tokens": 111,
    "completion_tokens": 1711,
    "total_tokens": 1822,
    "api_requests": 11
  },
  "breakdown": {
    "models": { "gpt-4o-mini": { "spend": 1.095e-05 } },
    "providers": { "openai": {}, "azure_ai": {} }
  }
}
```

---

## 6. Pre-Call Cost Estimation API

The `/cost/estimate` endpoint accepts `model`, `input_tokens`, and `output_tokens` and returns a per-request cost breakdown including input cost, output cost, and margin/fee — plus daily and monthly aggregates if request volume is provided. Results can be exported as PDF or CSV.

```bash
curl -X POST "http://localhost:4000/cost/estimate" \
  -H "Authorization: Bearer sk-1234" \
  -d '{ "model": "gpt-4", "input_tokens": 1000, "output_tokens": 500 }'
```

---

## 7. Registering Custom / Override Pricing

```python
import litellm

# Register a single model override
litellm.register_model({
    "my-fine-tuned-model": {
        "max_tokens": 8192,
        "input_cost_per_token": 0.00002,
        "output_cost_per_token": 0.00006,
        "litellm_provider": "openai",
        "mode": "chat"
    }
})

# Or load the full community pricing map from URL
litellm.register_model(
    model_cost="https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"
)
```

If you have firewalls and want to use just the local copy of the model cost map without pulling from the hosted URL, LiteLLM supports that too — though it means you'll need to upgrade the package to get updated pricing for newer models.

---

## Key Takeaway for Observability

Since `response._hidden_params["response_cost"]` is populated on every completion call, it's the cleanest hook for emitting cost as a custom OTel span attribute — no extra API calls needed.

```python
response = litellm.completion(model="gpt-3.5-turbo", messages=messages)

# Emit as OTel span attribute
span.set_attribute("llm.cost_usd", response._hidden_params["response_cost"])
span.set_attribute("llm.prompt_tokens", response.usage.prompt_tokens)
span.set_attribute("llm.completion_tokens", response.usage.completion_tokens)
span.set_attribute("llm.total_tokens", response.usage.total_tokens)
```
