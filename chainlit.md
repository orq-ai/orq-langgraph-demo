## Hybrid Data Agent

Welcome to the **Hybrid Data Agent** — a reference implementation of a LangGraph agent wired end-to-end to the orq.ai platform. It's an **internal ops assistant for a food-delivery service** and answers questions that span **structured order data** (SQLite — dishes, restaurants, cities, monthly aggregates) and **unstructured operational documents** (menu book, refund & SLA policy, food safety policy, allergen labeling policy, delivery operations handbook, customer service playbook — stored in the orq.ai Knowledge Base).

### What this assistant can do

- **Query delivery order data** — top dishes, order volume per city, cuisine performance, restaurant rankings, monthly trends, revenue, ratings, delivery times
- **Search operational documents** — refund eligibility rules, driver protocols, allergen info, food-safety temperature bands, customer-service escalation flows
- **Hybrid analysis** — combine both sources for questions that need *both* numbers *and* policy/menu context

### Example questions

- **Top dishes**: *"Top 5 dishes by order count in Berlin for 2024"*
- **Refund policy**: *"What is our refund policy for orders delivered more than 60 minutes late?"*
- **Allergens**: *"What allergens are listed for the Margherita Pizza?"*
- **Driver protocol**: *"How should drivers handle a contactless delivery when the customer is not responsive?"*
- **Hybrid**: *"How is Margherita Pizza performing in sales for 2024 and what allergens does it contain?"*

Available PDFs: Menu Book, Refund & SLA Policy, Food Safety & Hygiene Policy, Allergen Labeling Policy, Delivery Operations Handbook, Customer Service Playbook.

### Architecture overview

- **LangGraph agent** with conditional routing, a tool loop, and an input safety node
- **orq.ai AI Router** for all LLM calls — cost tracking, fallbacks, multi-provider access via one endpoint
- **orq.ai Knowledge Base** — managed chunking, embeddings, and hybrid search
- **orq.ai Prompts** — versioned system prompts, A/B-testable against the eval dataset
- **orq.ai Traces** — full LangGraph execution tree (callback handler by default, OpenTelemetry exporter optional), with cost + latency per node
- **Whitelisted SQL tools** — the agent picks from a fixed set of parameterized query types; no free-form SQL

### Security posture

- **Input safety** — every user message is classified by an **orq.ai LLM evaluator** (`ORQ_SAFETY_EVALUATOR_ID`) before the agent does any work. Unsafe inputs are blocked with a refusal. If the evaluator is unreachable, the guardrail fails open to OpenAI Moderation as a fallback.
- **Read-only, whitelisted SQL** — the agent never writes SQL. It calls typed tools that map to predefined query types in `sql_schemas.py`, parameters are validated, and the SQLite database is opened with `mode=ro`. No injection surface, no destructive writes.
- **Off-topic routing** — the router node classifies queries as `on_topic`, `more-info`, or `general`. Off-topic prompts are answered with a polite refusal by a dedicated node, which blunts prompt-injection and jailbreak attempts.
- **Grounded responses** — the system prompt requires the agent to cite the source (document name or tool output) for every factual claim. The `source-citations`, `response-grounding`, and `hallucination-check` evaluators verify this in the eval pipeline.
