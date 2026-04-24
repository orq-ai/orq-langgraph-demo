# LangGraph agent vs managed orq.ai Agent

This repo ships **two implementations** of the same assistant so you can
compare the trade-offs of building agents in code vs. in the orq.ai Studio:

| Approach | Entry point | How to run |
|---|---|---|
| **A — LangGraph agent** (code-first) | [`src/chainlit_app.py`](../src/chainlit_app.py) + [`src/assistant/graph.py`](../src/assistant/graph.py) | `make run` |
| **B — Managed orq.ai Agent** (Studio-first) | [`src/chainlit_app_orq.py`](../src/chainlit_app_orq.py) + [`src/orq_agent.py`](../src/orq_agent.py) | `make run-orq-agent` |

Both approaches talk to the **same Knowledge Base** (`hybrid-data-agent-kb`),
use the **same OpenAI model** (`gpt-4.1-mini` via the orq.ai Router), and
emit traces to the **same orq.ai Studio project**. The difference is where
the orchestration logic lives.

---

## Side-by-side

| Dimension | Approach A: LangGraph | Approach B: Managed orq.ai Agent |
|---|---|---|
| **Where the logic lives** | Python code (`src/assistant/graph.py`) | orq.ai Studio (agent config + instructions) |
| **Iteration loop** | Git push → CI → deploy | Edit in Studio → Publish → takes effect immediately |
| **Versioning** | Git commits | Studio version history + environment tags |
| **System prompt** | Fetched from orq.ai Prompts via `get_system_prompt()` with local fallback | Stored on the agent itself as `instructions` field |
| **Tool definitions** | Arbitrary Python functions decorated with `@tool` | Orq built-in tools (KB search, web search, etc.) + MCP + HTTP tools registered in the Studio |
| **Arbitrary Python tools** | ✅ Any function can be a tool (`search_documents`, `get_top_dishes`, `get_orders_by_dish`, etc.) | ❌ Needs an MCP server or HTTP tool wrapper to call repo code |
| **Custom routing / conditional edges** | ✅ Explicit `StateGraph` nodes (`guard_input → router → call_model → tools → call_model`) | ⚠️ Implicit — the agent LLM decides based on instructions |
| **State management** | LangGraph state machine (`State` dataclass, typed transitions) | orq.ai Memory Stores (when configured) |
| **Observability** | Via the orq.ai tracing integration → Traces (one graph tree per invocation). Callback handler by default, OTEL exporter alternative — see [LANGGRAPH-INTEGRATION.md](LANGGRAPH-INTEGRATION.md) | Native — every step is captured automatically in Traces |
| **Guardrails** | `OrqSafetyGuardrail` called from `guard_input` node | Attach evaluator as guardrail directly to the agent config |
| **Cost tracking** | Via router usage data per span | Same, plus agent-level aggregates in the Studio |
| **Multi-agent coordination** | ✅ Easy (compose multiple `StateGraph`s) | ✅ Via sub-agent calls in the Studio, but less flexible |
| **Offline development** | ✅ Runs against the KB/prompt, falls back to local strings if orq.ai is unreachable | ❌ Requires a live orq.ai connection for every call |

---

## When to pick Approach A (LangGraph)

Pick the code-first LangGraph approach when:

1. **You need explicit routing or conditional edges** — our `guard_input →
   route → call_model → tools → call_model` loop has strict ordering and
   safety-first design. A managed agent LLM can drift on this.
2. **You have arbitrary Python tools** — our 9 SQL tools
   (`get_orders_by_dish`, `get_top_dishes`, `get_cuisine_analysis`, etc.)
   are Python functions with parameterized queries. Exposing them through
   a managed agent requires wrapping each as an MCP server or HTTP tool.
3. **You need state machines with typed transitions** — LangGraph's
   `StateGraph` gives you compile-time guarantees about graph topology.
4. **You want git as the source of truth** — for regulated environments
   where every change to agent logic needs review + audit.
5. **You want the full multi-agent toolbox** — LangGraph supports
   supervisor patterns, parallel branches, interrupts, human-in-the-loop,
   checkpointing, persistence to Redis/Postgres, etc.

---

## When to pick Approach B (managed Agent)

Pick the Studio-first managed Agent when:

1. **You're iterating on prompts and want product teams to edit** —
   non-engineers can safely modify instructions in the Studio without
   touching code.
2. **Your tools are standard** — web search, KB retrieval, scraping, MCP
   tools. The Studio registry covers most use cases.
3. **You want built-in A/B testing of agent configs** — Studio lets you
   fork and run experiments against datasets without code changes.
4. **You want the managed infrastructure** — memory stores, streaming,
   background execution, human-in-the-loop approval queues, rate limiting,
   all handled by orq.ai.
5. **You want fast time-to-first-demo** — clone this repo, run
   `make setup-workspace`, answer in the Studio, point a client at it.

---

## What "same question" looks like in both

Ask: **"What allergens are listed for the Margherita Pizza?"**

### Approach A — LangGraph

```
Hybrid Data Agent
├── guard_input (orq.ai safety evaluator)
├── analyze_and_route_query → on_topic
├── call_model (ChatOpenAI)
│   └── tool_call: search_documents("Margherita Pizza allergens")
├── tools (search_documents)
│   └── orq_ai_sdk: client.knowledge.search(knowledge_id=..., query=...)
└── call_model (final response with citation to the Menu Book)
```

Full execution tree visible in orq.ai Traces under `Hybrid Data Agent`.
Every node is a Python function in `src/assistant/`.

### Approach B — Managed Agent

```
hybrid-data-agent-managed
├── instructions evaluated
├── tool: retrieve_knowledge_bases
├── tool: query_knowledge_base
└── final response
```

Full execution tree visible in orq.ai Traces under `hybrid-data-agent-managed`.
No Python code is involved beyond the thin invoker in `src/orq_agent.py`
which calls `client.agents.responses.create_async(...)` on the orq-ai-sdk client.

---

## Caveat on Approach B in this repo

The managed Agent we create via `make setup-workspace` is **document-only**.
It doesn't have access to the 9 SQL tools the LangGraph agent uses, because
those tools are Python functions in this repo, not registered in the orq.ai
tool registry.

To make Approach B fully equivalent, you'd need to:

1. Expose each SQL tool as an MCP server or HTTP endpoint
2. Register them in the orq.ai Studio under Tools
3. Attach them to the agent's tools list

That work is out of scope for this reference but it's documented in
[orq.ai → Tools](https://docs.orq.ai/docs/tools/overview).

---

## Recommended reading

- [orq.ai Agents documentation](https://docs.orq.ai/docs/agents/overview)
- [orq.ai Agents Framework & API guide](https://docs.orq.ai/docs/common-architecture/agents-framework-guide)
- [LangGraph docs](https://langchain-ai.github.io/langgraph/)
- [This repo's LangGraph graph](../src/assistant/graph.py)
- [This repo's managed agent setup](../scripts/setup_orq_workspace.py) — `setup_managed_agent()`
