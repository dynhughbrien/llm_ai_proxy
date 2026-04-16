
# Minimum Effective Dose of AI (LLMs)

## Why Minimum Effective Dose?
- Avoid over-engineering
- Reduce cost and operational risk
- Focus on measurable value

## LLMs Are Black Boxes
- Opaque internal logic
- Not debuggable
- Treat as external dependencies

## LLMs Are Just HTTP APIs
- HTTP requests
- JSON payloads
- Standard API integration

## Tokens In / Tokens Out
- Input tokens drive cost
- Output tokens drive latency
- Optimize prompts first

## Requests & Responses Have Parameters
- Temperature
- Max tokens
- Sampling controls

## AI Frameworks
- Abstract HTTP calls
- Simplify orchestration
- Do not change fundamentals

## AI Applications Are Still Software
- Standard architecture
- APIs, error handling, security
- AI is just another dependency

## Multiple LLM Calls
- Pipelines and stages
- More calls = more failure points
- Design for resilience

## Why Observability Matters
- Non-deterministic behavior
- High cost variability
- Latency sensitivity

## Why OpenTelemetry (OTEL)
- Traces LLM calls
- Measures token usage
- Enables cost and performance insights

## Final Takeaway
**Use the minimum effective dose of AI.**
Engineering discipline beats hype.
