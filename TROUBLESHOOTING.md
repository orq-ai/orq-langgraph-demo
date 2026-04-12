# Troubleshooting

Real issues encountered while building this repo, with root causes and workarounds. If you hit one of these, `make doctor` should surface it with a clear remediation — this doc explains *why*.

---

## SDK vs API drift

The installed `orq-ai-sdk` ships with Pydantic models that lag behind the actual REST API in a few places. When that happens, typed SDK calls fail with validation errors or silently strip fields. The workaround throughout this repo is **raw HTTP via `httpx`** for the affected endpoints.

### Knowledge Base creation requires `type: "internal"`

**Symptom:**
```
orq_ai_sdk.models.apierror.APIError: Status 400
{"error":"Validation error: Invalid input at \"type\""}
```

**Root cause:** The SDK's `CreateKnowledgeRequestBody` doesn't include the `type` field, but the API requires it (values: `"internal"` or `"external"`).

**Workaround:** We create the KB via raw HTTP in [`scripts/setup_orq_workspace.py`](scripts/setup_orq_workspace.py) (`setup_knowledge_base`) and in [`scripts/unstructured_data_ingestion_pipeline.py`](scripts/unstructured_data_ingestion_pipeline.py) (`_create_knowledge_base`).

### Prompt create uses `prompt`, SDK expects `prompt_config`

**Symptom on create:**
```
APIError: Status 400
{"error":"Validation error: Invalid input: expected object, received undefined at \"prompt\""}
```

**Symptom on retrieve:**
```
3 validation errors for Unmarshaller
body.prompt_config
  Field required [type=missing, input_value={'_id': '01K...', 'prompt': {...}}]
```

**Root cause:** The SDK's typed models expect `prompt_config` in both the request and response, but the API uses `prompt`. Create is rejected; retrieve fails to parse.

**Workaround:** [`scripts/setup_orq_workspace.py`](scripts/setup_orq_workspace.py) (`setup_system_prompt`) and [`src/assistant/prompts.py`](src/assistant/prompts.py) (`get_system_prompt`) both use raw HTTP.

### `CreateChunkMetadata` silently strips custom fields

**Symptom:** Chunks upload successfully but the metadata dict on the server only contains `page_number` — all your other fields (`filename`, `chunk_id`, `chunk_index`, etc.) disappear.

**Root cause:** The SDK's `CreateChunkMetadata` Pydantic model only declares `page_number` and uses Pydantic's default behavior (strip unknown fields). Even though the API accepts arbitrary metadata, the SDK strips it before sending.

**Workaround:** Chunks are uploaded via raw HTTP in [`scripts/unstructured_data_ingestion_pipeline.py`](scripts/unstructured_data_ingestion_pipeline.py) (`_upload_chunks`).

---

## OpenTelemetry tracing

### Traces appear fragmented / flat (individual LLM spans, no graph tree)

**Symptom:** In orq.ai Studio → Traces you see individual `ChatOpenAI` spans but no parent `RAG Assistant` / `call_model` / `tools` hierarchy.

**Root cause:** The `BatchSpanProcessor` queues spans and flushes them asynchronously. In short-lived scripts (like `make evals-run`) the process exits before the queue drains, so spans are dropped or arrive without their parent context.

**Fix:** Register an `atexit` handler that calls `provider.force_flush()`:
```python
import atexit
_provider = TracerProvider()
_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(_provider)
atexit.register(lambda: _provider.force_flush(timeout_millis=10_000))
```

See [`src/assistant/tracing.py`](src/assistant/tracing.py).

### `LANGSMITH_OTEL_ENABLED` is required for LangGraph traces

**Symptom:** You set up the OTEL exporter but LangGraph nodes never appear as spans.

**Root cause:** LangChain/LangGraph's built-in tracer is **off by default**. The three env vars that turn it on also look like they route to LangSmith — but with `LANGSMITH_OTEL_ONLY=true` they route to the OTEL exporter (i.e. *your* orq.ai endpoint) instead of LangSmith.

**Required setup** (see [`src/assistant/tracing.py`](src/assistant/tracing.py)):
```python
os.environ["LANGSMITH_OTEL_ENABLED"] = "true"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_OTEL_ONLY"] = "true"
```

Despite the naming, nothing is ever sent to LangSmith with this combination.

### Import order matters: setup tracing **before** importing langchain/evaluatorq

**Symptom:** Traces from the eval pipeline appear incomplete while traces from Chainlit look fine.

**Root cause:** LangSmith's OTEL hooks register with whatever `TracerProvider` is the global default at the time langchain is first imported. If you `import langchain_core` before calling `setup_tracing()`, the hooks register against the default no-op provider and never see your real exporter.

**Fix:** Always call `setup_tracing()` **before** importing anything that transitively pulls in `langchain_core`, `langsmith`, or `evaluatorq`. See the import order in [`evals/run_evaluation_pipeline.py`](evals/run_evaluation_pipeline.py):
```python
load_dotenv()
from assistant.tracing import setup_tracing  # noqa: E402
setup_tracing()
from evaluatorq import ...  # noqa: E402
from langchain_core.messages import HumanMessage  # noqa: E402
```

---

## Knowledge Base

### Chunk upload limit is 100 per request

**Symptom:**
```
Status 400
{"error":"Validation error: Too big: expected array to have <=100 items"}
```

**Root cause:** The `POST /v2/knowledge/{id}/datasources/{id}/chunks` endpoint caps the request body at 100 items. The docs also mention a 5000-item bulk endpoint but that one uses a different path.

**Fix:** Use a batch size of 100 in [`scripts/unstructured_data_ingestion_pipeline.py`](scripts/unstructured_data_ingestion_pipeline.py) (`ingest_pdf_directory`, `batch_size = 100`).

### Searches return 0 results right after ingestion

**Symptom:** You just ran `make ingest-kb`, it reported success, but `make doctor` or a live search returns no matches.

**Root cause:** orq.ai embeds chunks **asynchronously** after they're uploaded. Chunks land in `status: "pending"` and move to `status: "completed"` once the embedding job finishes (usually within a minute for small datasets).

**Fix:** Wait ~1 minute after `make ingest-kb` before searching, or check chunk status in the Studio under `langgraph-demo` → Knowledge Base → datasource → chunks column.

### `scores` and `metadata` missing from search response

**Symptom:** `_kb_search()` returns matches but `score=0.0` and `metadata={}`.

**Root cause:** By default the search endpoint returns only `id` and `text`. To get scores and metadata, you must pass `search_options`.

**Fix:** Include both keys in the payload (see [`src/assistant/tools.py`](src/assistant/tools.py) `_kb_search`):
```python
payload = {
    "query": query,
    "retrieval_config": {"type": "hybrid_search", "top_k": top_k},
    "search_options": {"include_metadata": True, "include_scores": True},
}
```

Scores come back under `scores.search_score` and `scores.rerank_score` (not top-level `score`).

### `retrieval_config` requires a `type` field

**Symptom:**
```
3 validation errors for Unmarshaller
body.RetrievalConfig1.type
  Field required [type=missing, input_value={'top_k': 5}]
```

**Root cause:** The SDK's `retrieval_config` type union requires explicit `type`: one of `"vector_search"`, `"keyword_search"`, or `"hybrid_search"`.

**Fix:** Always pass `{"type": "hybrid_search", "top_k": N}` (or one of the other two). See [`src/assistant/tools.py`](src/assistant/tools.py) `_kb_search`.

---

## Datasets

### Inputs must be flat primitives

**Symptom:**
```
Status 400
{"error":"Validation error: Invalid input: expected array, received object"}
```

**Root cause:** Dataset `inputs` are indexed as a flat key-value map. Nested objects and arrays are rejected by the API.

**Fix:** Serialize non-primitive values to JSON strings before uploading (see [`scripts/setup_orq_workspace.py`](scripts/setup_orq_workspace.py) `_load_datapoints`):
```python
flat_inputs = {
    k: json.dumps(v) if isinstance(v, (list, dict)) else v
    for k, v in inputs.items()
}
```

On the consuming side (eval pipeline), parse them back:
```python
raw = data.inputs.get("expected_tools", [])
expected_tools = json.loads(raw) if isinstance(raw, str) else raw
```

### `create_datapoint` SDK signature quirk

**Symptom:**
```
TypeError: Datasets.create_datapoint() got an unexpected keyword argument 'request_body'
```

**Root cause:** In the installed SDK, `create_datapoint` takes **flat kwargs** (`dataset_id`, `inputs`, `messages`, `expected_output`) — not a `request_body` list. Bulk upload uses a separate method `create_datapoints` (plural) with an `items` parameter. The GitHub docs show an older signature.

**Fix:** Use the bulk endpoint for multiple datapoints (see [`scripts/setup_orq_workspace.py`](scripts/setup_orq_workspace.py) `setup_dataset`) via raw HTTP against `/v2/datasets/{id}/datapoints/bulk`, or call `create_datapoint` once per datapoint via the SDK.

### List endpoints are paginated — a small workspace easily overflows the default limit

**Symptom:** Bootstrap script always creates a new entity even though an identically-named one already exists.

**Root cause:** `/v2/datasets`, `/v2/prompts`, `/v2/knowledge` all return at most 50 items per call with cursor pagination via `starting_after`. If your workspace has more than 50 entities, your lookup never finds the match.

**Fix:** Paginate until `has_more` is false (see [`scripts/setup_orq_workspace.py`](scripts/setup_orq_workspace.py) `_paginate` helper).

---

## Dotenv file gotchas

### `python-dotenv` warns about malformed lines

**Symptom:**
```
Python-dotenv could not parse statement starting at line 11
```

**Root cause:** A non-empty line in `.env` that isn't `KEY=VALUE`, `KEY="VALUE"`, or a `#` comment. Common cause: pasting multi-line output from a script that wasn't purely env-var format.

**Fix:** Open `.env`, find line 11, remove or comment it with `#`. `make doctor` catches this automatically. The bootstrap script now prints a paste-safe block where every non-env-var line is already commented.

---

## Evaluation pipeline

### `Llm end error: argument of type 'NoneType' is not iterable`

**Symptom:** The `OrqLangchainCallback` prints this error in evals runs but the scores still come out correct.

**Root cause:** A known bug in the installed SDK callback — `on_llm_end` iterates `response.llm_output` which can be `None` on certain LangGraph paths. The error is non-fatal, but the noise is annoying.

**Fix:** We removed the callback from the compiled graph entirely and rely on OTEL for tracing instead. See [`src/assistant/graph.py`](src/assistant/graph.py) — `builder.compile(name="Hybrid Data Agent")` has no `.with_config({"callbacks": [...]})`.

### `Error in LangchainTracer.on_llm_end callback: TypeError('Object of type ModelMetaclass is not JSON serializable')`

**Symptom:** Same as above but from LangChain's built-in `LangchainTracer`, not our code.

**Root cause:** LangChain's `LangchainTracer` (auto-activated by `LANGSMITH_TRACING=true`) tries to JSON-serialize the LLM response metadata, which includes a Pydantic model class reference. Upstream bug, non-fatal.

**Fix:** Raise the log level for the noisy logger so the warning stays out of terminal output (see [`src/chainlit_app.py`](src/chainlit_app.py)):
```python
logging.getLogger("langchain_core.callbacks.manager").setLevel(logging.ERROR)
```

---

## Getting help

If you hit something not listed here:

1. **Run `make doctor`** first — most setup issues are caught automatically.
2. **Check the orq.ai Studio** for the failing entity (trace, KB, dataset) — error context is usually clearer there than in logs.
3. **Check the span tree** — if the agent misbehaves, the full LangGraph execution tree in the Traces tab will show exactly which node produced the bad output.
4. **File an issue** on this repo describing the symptom and what `make doctor` reported.
