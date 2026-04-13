"""Knowledge Base tools — semantic document search via orq.ai.

All tools here talk to the orq.ai Knowledge Base REST API directly via
`httpx` rather than the SDK, because the installed SDK's search response
model is out of sync with the API (expects `knowledge_id`/`documents`/`query`
fields while the API returns `matches`).
"""

import logging
import os
from typing import Any, Callable, Dict, List, Optional

import httpx
from langchain_core.tools import tool
from orq_ai_sdk import Orq

from core.settings import settings

from .models import SearchResult

logger = logging.getLogger(__name__)


# Global orq.ai client for lazy initialization
_orq_client: Optional[Orq] = None


def _get_orq_client() -> Optional[Orq]:
    """Lazy initialization of the orq.ai client."""
    global _orq_client
    if _orq_client is not None:
        return _orq_client

    api_key = os.environ.get("ORQ_API_KEY")
    if not api_key:
        logger.warning("ORQ_API_KEY not set — knowledge base search unavailable")
        return None

    if not settings.ORQ_KNOWLEDGE_BASE_ID:
        logger.warning(
            "ORQ_KNOWLEDGE_BASE_ID not set — run the ingestion pipeline first and "
            "set ORQ_KNOWLEDGE_BASE_ID in .env"
        )
        return None

    _orq_client = Orq(api_key=api_key)
    logger.debug(f"orq.ai client initialized - KB: {settings.ORQ_KNOWLEDGE_BASE_ID}")
    return _orq_client


def _kb_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    """Call the orq.ai Knowledge Base search REST API directly.

    Returns a list of match dicts with keys: id, text, metadata, scores.
    """
    api_key = os.environ.get("ORQ_API_KEY")
    url = f"https://api.orq.ai/v2/knowledge/{settings.ORQ_KNOWLEDGE_BASE_ID}/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "query": query,
        "retrieval_config": {"type": "hybrid_search", "top_k": top_k},
        "search_options": {"include_metadata": True, "include_scores": True},
    }
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    body = response.json()
    return body.get("matches") or body.get("documents") or []


def _match_to_search_result(match: Dict[str, Any]) -> SearchResult:
    """Convert a raw KB search match dict to a SearchResult."""
    metadata = match.get("metadata") or {}
    scores = match.get("scores") or {}
    # orq.ai returns scores as {"search_score": ..., "rerank_score": ...}
    score_value = (
        scores.get("rerank_score")
        if scores.get("rerank_score") is not None
        else scores.get("search_score")
    )
    if score_value is None:
        score_value = match.get("score") or 0.0
    return SearchResult(
        filename=metadata.get("filename") or metadata.get("file_name") or "Unknown",
        page=int(metadata.get("page_number") or 0),
        chunk_index=int(metadata.get("chunk_index") or 0),
        content=match.get("text") or "",
        relevance_score=float(score_value),
        chunk_id=metadata.get("chunk_id") or match.get("id") or "",
    )


def _format_search_results_for_llm(results: List[SearchResult]) -> str:
    """Render SearchResults as a string the LLM can cite from.

    The full SearchResult objects ride alongside as a ToolMessage artifact
    (see `response_format="content_and_artifact"` below) so the Chainlit UI
    can render PDF previews without needing to parse this string.
    """
    if not results:
        return "No matches."
    return "\n\n".join(f"[{r.filename} p.{r.page}] {r.content}" for r in results)


@tool(
    response_format="content_and_artifact",
    description="""Use this tool to answer questions about warranty terms, policy clauses, or owner's manual content by searching the document database.

IMPORTANT: When you use this tool to answer a question, you MUST:
1. Provide a comprehensive answer based on the retrieved content

Args:
    query: The search query string
    limit: Maximum number of results to return (default: 10)
Returns:
    List of relevant document chunks with metadata including filename and page numbers for citation""",
)
def search_documents(
    query: str, limit: int = settings.MAX_SEARCH_RESULTS
) -> tuple[str, List[SearchResult]]:
    """Returns (llm_visible_content, structured_artifact).

    The artifact rides on the ToolMessage and is consumed by the Chainlit
    UI to render PDF previews (see chainlit_app.py).
    """
    if _get_orq_client() is None:
        return "Knowledge base unavailable.", []
    try:
        matches = _kb_search(query, top_k=limit)
        results = [_match_to_search_result(m) for m in matches]
        logger.info(f"orq.ai KB search found {len(results)} results for query: '{query}'")
        return _format_search_results_for_llm(results), results
    except Exception as e:
        logger.error(f"orq.ai KB search error: {e}")
        return f"Search error: {e}", []


@tool
def list_available_documents() -> List[Dict[str, Any]]:
    """List all available documents in the knowledge base.

    Returns:
        List of document information including filename and datasource ID.
    """
    client = _get_orq_client()
    if not client:
        return []
    try:
        response = client.knowledge.list_datasources(
            knowledge_id=settings.ORQ_KNOWLEDGE_BASE_ID,
            limit=50,
        )
        data = getattr(response, "data", []) or []
        documents = [
            {
                "filename": getattr(ds, "display_name", None) or "Unknown",
                "datasource_id": getattr(ds, "id", None) or getattr(ds, "_id", ""),
            }
            for ds in data
        ]
        logger.info(f"Listed {len(documents)} available documents from orq.ai KB")
        return documents
    except Exception as e:
        logger.error(f"Error listing documents from orq.ai KB: {e}")
        return []


@tool(
    response_format="content_and_artifact",
    description="""Search within a specific document for relevant content.

IMPORTANT: When you use this tool to answer a question, you MUST:
1. Provide a comprehensive answer based on the retrieved content from the specified document

Args:
    filename: Name of the document to search in
    query: The search query string
    limit: Maximum number of results to return (default: 3)
Returns:
    List of relevant chunks from the specified document with page numbers for citation""",
)
def search_in_document(filename: str, query: str, limit: int = 3) -> tuple[str, List[SearchResult]]:
    """Returns (llm_visible_content, structured_artifact)."""
    if _get_orq_client() is None:
        return "Knowledge base unavailable.", []
    try:
        # Fetch broader results and filter client-side by filename.
        matches = _kb_search(query, top_k=20)

        filtered = []
        for match in matches:
            match_metadata = match.get("metadata") or {}
            doc_filename = match_metadata.get("filename") or match_metadata.get("file_name") or ""
            if filename.lower() in doc_filename.lower() or doc_filename.lower() in filename.lower():
                filtered.append(match)
                if len(filtered) >= limit:
                    break

        results = [_match_to_search_result(m) for m in filtered]
        logger.info(
            f"orq.ai KB search found {len(results)} results in {filename} for query: '{query}'"
        )
        return _format_search_results_for_llm(results), results
    except Exception as e:
        logger.error(f"orq.ai KB search error in document {filename}: {e}")
        return f"Search error: {e}", []


KB_TOOLS: List[Callable[..., Any]] = [
    search_documents,
    list_available_documents,
    search_in_document,
]
