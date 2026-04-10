# Plan: Replace ChromaDB with orq.ai Knowledge Base API

## Context

This project uses ChromaDB (local + cloud) as the vector store for a Toyota/Lexus RAG assistant. The goal is to replace ChromaDB with the orq.ai Knowledge Base API so that:
- Document storage, embeddings, and search are fully managed by orq.ai
- We keep our existing PDF loading and chunking logic (PyPDF + RecursiveCharacterTextSplitter)
- We send chunks to orq.ai instead of ChromaDB
- We query orq.ai's search API instead of ChromaDB's similarity search

**orq.ai Knowledge Base concepts:**
- **Knowledge Base** = a named collection with an embedding model (like a ChromaDB collection)
- **Datasource** = a logical grouping within a KB (e.g., one per PDF file)
- **Chunk** = a piece of text with optional metadata (like a ChromaDB document)
- **Search** = `client.knowledge.search(knowledge_id, query)` returns matches with text + metadata + scores

**Reference docs:** https://docs.orq.ai/docs/knowledge/overview and https://docs.orq.ai/docs/knowledge/api

---

## Phase 1: Ingestion Pipeline — Replace ChromaDB storage with orq.ai

**Why:** `scripts/unstructured_data_ingestion_pipeline.py` currently loads PDFs, chunks them with `RecursiveCharacterTextSplitter`, adds metadata, and stores in ChromaDB via `vectorstore.add_documents()`. We keep all the loading/chunking/metadata logic but send chunks to orq.ai instead.

### Files to modify

- **`scripts/unstructured_data_ingestion_pipeline.py`** — Replace ChromaDB client with orq.ai SDK calls

### Changes

The `ChromaPDFIngestionPipeline` class gets renamed to `OrqPDFIngestionPipeline`. Key method changes:

1. **`__init__`** — Replace ChromaDB config with `orq_api_key` and `knowledge_base_id`. Initialize `Orq` client.

2. **`_setup_database()`** — Remove local directory creation/deletion. Instead, optionally create the Knowledge Base via `client.knowledge.create()` if `knowledge_base_id` is not provided.

3. **`_get_vectorstore()`** → **Remove entirely**. No more ChromaDB vectorstore.

4. **`_process_single_pdf()`** — Keep as-is. Still uses PyPDFLoader + RecursiveCharacterTextSplitter + metadata enrichment. Returns `List[Document]` exactly as before.

5. **`ingest_pdf_directory()`** — Replace the batch `vectorstore.add_documents()` calls with:
   - Create a datasource per PDF: `client.knowledge.create_datasource(knowledge_id, display_name=filename)`
   - Send chunks in batches: `client.knowledge.create_chunks(knowledge_id, datasource_id, request_body=[{"text": chunk.page_content, "metadata": chunk.metadata}])`

6. **`verify_ingestion()`** — Replace `vectorstore.similarity_search()` with `client.knowledge.search(knowledge_id, query=...)`

7. **`get_collection_stats()`** — Replace with `client.knowledge.retrieve(knowledge_id)` to get metadata.

### Chunking/Embedding notes

We have two options for chunking:
- **Option A (recommended):** Keep local `RecursiveCharacterTextSplitter` chunking and send pre-chunked text to orq.ai via `create_chunks()`. orq.ai handles embedding with the model configured on the KB.
- **Option B:** Use orq.ai's `client.chunking.parse()` API to do chunking server-side. This would remove our local chunking dependency but changes behavior.

**Recommendation: Option A** — Keep local chunking to preserve identical behavior during migration. orq.ai will embed the chunks using the embedding model set on the Knowledge Base (e.g., `openai/text-embedding-3-small`).

---

## Phase 2: Search/Retrieval — Replace ChromaDB queries with orq.ai search

**Why:** `src/assistant/tools.py` has three search functions that use `vectorstore.similarity_search_with_score()`. These need to call `client.knowledge.search()` instead.

### Files to modify

- **`src/assistant/tools.py`** — Replace ChromaDB vectorstore with orq.ai Knowledge Base search

### Changes

1. **Remove** `_get_vectorstore()`, `get_vectorstore()`, `get_collection_stats()`, and all ChromaDB imports (`langchain_chroma`, `chromadb`, `OpenAIEmbeddings`)

2. **Add** orq.ai client initialization:
   ```python
   from orq_ai_sdk import Orq
   
   _orq_client = None
   
   def _get_orq_client() -> Orq:
       global _orq_client
       if _orq_client is None:
           _orq_client = Orq(api_key=os.getenv("ORQ_API_KEY"))
       return _orq_client
   ```

3. **`search_documents(query, limit)`** — Rewrite to:
   ```python
   results = _get_orq_client().knowledge.search(
       knowledge_id=settings.ORQ_KNOWLEDGE_BASE_ID,
       query=query,
       search_options={"limit": limit, "include_metadata": True, "include_scores": True},
   )
   ```
   Map `results.matches` → `List[SearchResult]` using metadata fields.

4. **`search_in_document(filename, query, limit)`** — Use metadata filtering:
   ```python
   results = _get_orq_client().knowledge.search(
       knowledge_id=settings.ORQ_KNOWLEDGE_BASE_ID,
       query=query,
       filter_by={"filename": {"eq": filename}},
       search_options={"limit": limit, "include_metadata": True, "include_scores": True},
   )
   ```

5. **`list_available_documents()`** — This is trickier since orq.ai doesn't have a "list all metadata" query. Options:
   - Query with a broad term and aggregate metadata (current approach with ChromaDB)
   - Use `client.knowledge.list_datasources(knowledge_id)` since we create one datasource per PDF
   
   **Recommendation:** Use `list_datasources()` — cleaner and doesn't rely on search hacks.

---

## Phase 3: Configuration — Replace ChromaDB settings with orq.ai KB settings

### Files to modify

- **`src/core/settings.py`** — Replace ChromaDB settings with `ORQ_KNOWLEDGE_BASE_ID`
- **`.env.example`** / **`.env`** — Add `ORQ_KNOWLEDGE_BASE_ID`, remove ChromaDB vars
- **`pyproject.toml`** — Remove `chromadb` and `langchain-chroma` dependencies
- **`requirements.txt`** — Remove `chromadb`

### Changes

1. **`settings.py`** — Remove `CHROMA_DB_PATH`, `CHROMA_COLLECTION_NAME`, `CHROMA_API_KEY`, `CHROMA_TENANT_ID`, `CHROMA_DATABASE_NAME`. Add:
   ```python
   ORQ_KNOWLEDGE_BASE_ID: str = ""  # Set after creating KB
   ```
   Keep `EMBEDDING_MODEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP` (used by local chunking).

2. **`pyproject.toml`** — Remove `"langchain-chroma ~=0.2.3"` and `"chromadb >=1.1.0"` from dependencies

3. **`requirements.txt`** — Remove `chromadb>=1.1.0`

---

## Phase 4: Cleanup — Update docs and Makefile

### Files to modify

- **`README.md`** — Update architecture description and setup instructions
- **`ARCHITECTURE.md`** — Replace ChromaDB references with orq.ai Knowledge Base
- **`Makefile`** — Update `setup-embeddings-db` target to run the new ingestion pipeline
- **`Dockerfile`** / **`docker-compose.yml`** — Remove chroma_db volume mounts

---

## Verification

1. **Ingestion:** Run `make setup-embeddings-db` → should create KB + datasources + chunks on orq.ai. Verify in orq.ai Studio under Knowledge Bases.
2. **Search:** Run `make run`, ask "How do I check the engine oil in my RAV4?" → should return relevant document chunks from orq.ai KB.
3. **Filtered search:** Ask about a specific document → `search_in_document` should use metadata filter.
4. **No ChromaDB:** `grep -r "chromadb\|langchain_chroma\|Chroma" src/ scripts/` returns nothing.

---

## Dependency summary

| Add | Remove |
|---|---|
| (orq-ai-sdk already in deps) | `chromadb >=1.1.0` |
| | `langchain-chroma ~=0.2.3` |

---

## Key risk: `list_available_documents`

The current implementation does a broad ChromaDB search and aggregates metadata. With orq.ai, we should use `list_datasources()` instead (one datasource per PDF). This changes the implementation but keeps the same tool interface and return format. If datasource names aren't sufficient, we can fall back to a broad search + aggregation.
