## Hybrid Data Agent

Welcome to the **Hybrid Data Agent** — a reference implementation of a LangGraph agent wired end-to-end to the orq.ai platform. It answers questions that span **structured sales data** (SQLite) and **unstructured documents** (owner's manuals, warranty policies, contracts — stored in the orq.ai Knowledge Base).

### What this assistant can do

- **Query sales data** — monthly/yearly sales per model, country, region, powertrain, etc.
- **Search documents** — owner's manuals, warranty policies, and Toyota/Lexus 2023 contracts
- **Hybrid analysis** — combine both sources to answer questions that need sales numbers *and* policy/product context

### Example questions

- **Sales**: *"Monthly RAV4 HEV sales in Germany in 2024"*
- **Warranty**: *"What is the standard Toyota warranty for Europe?"*
- **Owner's manual**: *"Where is the tire repair kit located in a Toyota C-HR?"*
- **Safety features**: *"What safety features does the Yaris Cross have?"*
- **Hybrid**: *"How is RAV4 performing in sales and what maintenance does it require?"*

Available PDFs: RAV4 manual, Toyota C-HR manual, Yaris Cross manual, Warranty Policy Appendix, Toyota 2023 contract, Lexus 2023 contract.

### Architecture overview

- **LangGraph agent** with conditional routing, a tool loop, and an input safety node
- **orq.ai AI Router** for all LLM calls — cost tracking, fallbacks, multi-provider access via one endpoint
- **orq.ai Knowledge Base** — managed chunking, embeddings, and hybrid search
- **orq.ai Prompts** — versioned system prompts, A/B-testable against the eval dataset
- **orq.ai Traces** — full LangGraph execution tree via OpenTelemetry, with cost + latency per node
- **Whitelisted SQL tools** — the agent picks from a fixed set of parameterized query types; no free-form SQL

### Security posture

- **Input safety** — every user message is classified by an **orq.ai LLM evaluator** (`ORQ_SAFETY_EVALUATOR_ID`) before the agent does any work. Unsafe inputs are blocked with a refusal. If the evaluator is unreachable, the guardrail fails open to OpenAI Moderation as a fallback.
- **Read-only, whitelisted SQL** — the agent never writes SQL. It calls typed tools that map to predefined query types in `sql_schemas.py`, parameters are validated, and the SQLite database is opened with `mode=ro`. No injection surface, no destructive writes.
- **Off-topic routing** — the router node classifies queries as `toyota`, `more-info`, or `general`. Off-topic prompts are answered with a polite refusal by a dedicated node, which blunts prompt-injection and jailbreak attempts.
- **Grounded responses** — the system prompt requires the agent to cite the source (document name or tool output) for every factual claim. The `source-citations`, `response-grounding`, and `hallucination-check` evaluators verify this in the eval pipeline.
