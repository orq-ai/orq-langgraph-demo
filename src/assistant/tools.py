"""This module provides Toyota RAG tools for document search and SQL queries.

These tools are designed for Toyota/Lexus vehicle information and sales data analysis.
Uses ChromaDB for semantic document search and SQLite for sales data queries.
"""

import logging
import os
import sqlite3
from typing import Any, Callable, Dict, List, Optional

from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings

from core.settings import settings

from .models import SearchResult
from .sql_tools import INDIVIDUAL_SQL_TOOLS

logger = logging.getLogger(__name__)


# Global variables for lazy initialization
vectorstore = None


def _get_vectorstore() -> Optional[Chroma]:
    """Lazy initialization of ChromaDB vectorstore with support for both local and cloud."""
    global vectorstore

    if vectorstore is not None:
        return vectorstore

    try:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(
            model=settings.EMBEDDING_MODEL, openai_api_key=os.environ.get("OPENAI_API_KEY")
        )

        if settings.CHROMA_API_KEY and settings.CHROMA_API_KEY.strip():
            # Use ChromaDB Cloud
            logger.info("Connecting to ChromaDB Cloud...")
            import chromadb

            chroma_client = chromadb.CloudClient(
                api_key=settings.CHROMA_API_KEY,
                tenant=settings.CHROMA_TENANT_ID,
                database=settings.CHROMA_DATABASE_NAME,
            )

            vectorstore = Chroma(
                client=chroma_client,
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embeddings,
            )
            logger.info(
                f"Connected to ChromaDB Cloud - collection: {settings.CHROMA_COLLECTION_NAME}"
            )

        else:
            # Use local ChromaDB
            if not settings.CHROMA_DB_PATH.exists():
                logger.warning(f"Local ChromaDB not found at {settings.CHROMA_DB_PATH}")
                return None

            vectorstore = Chroma(
                collection_name=settings.CHROMA_COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=str(settings.CHROMA_DB_PATH),
            )
            logger.info(f"Connected to local ChromaDB at {settings.CHROMA_DB_PATH}")

        # Get document count for logging
        try:
            doc_count = vectorstore._collection.count()
            logger.info(
                f"ChromaDB collection '{settings.CHROMA_COLLECTION_NAME}' has {doc_count} documents"
            )
        except Exception as count_e:
            logger.debug(f"Could not get document count: {count_e}")

        return vectorstore

    except Exception as e:
        logger.warning(f"Failed to connect to ChromaDB: {e}")
        return None


def _get_sqlite_connection():
    """Create a new SQLite connection for each request to avoid threading issues.

    This function creates a fresh connection for every request to prevent
    'SQLite objects created in a thread can only be used in that same thread' errors
    that occur when the same connection is reused across different conversation turns.
    """
    try:
        # Create a new connection each time to avoid threading issues
        # check_same_thread=False allows the connection to be used across threads
        # mode=ro ensures read-only access for safety
        conn = sqlite3.connect(
            f"file:{settings.DEFAULT_SQLITE_PATH}?mode=ro",
            uri=True,
            check_same_thread=False,
            timeout=30.0,  # Add timeout to prevent hanging
        )
        logger.debug(f"Created new SQLite connection to {settings.DEFAULT_SQLITE_PATH}")
        return conn
    except Exception as e:
        logger.warning(f"Failed to connect to SQLite: {e}")
        return None


@tool(
    description="""Use this tool to answer questions about warranty terms, policy clauses, or owner's manual content by searching the document database.

IMPORTANT: When you use this tool to answer a question, you MUST:
1. Provide a comprehensive answer based on the retrieved content

Args:
    query: The search query string
    limit: Maximum number of results to return (default: 10)
Returns:
    List of relevant document chunks with metadata including filename and page numbers for citation"""
)
def search_documents(query: str, limit: int = settings.MAX_SEARCH_RESULTS) -> List[SearchResult]:
    vectorstore = _get_vectorstore()
    if not vectorstore:
        return []
    try:
        # Use ChromaDB similarity search with scores
        results_with_scores = vectorstore.similarity_search_with_score(query=query, k=limit)
        search_results = []

        for doc, score in results_with_scores:
            # Extract metadata from the document
            metadata = doc.metadata
            result = SearchResult(
                filename=metadata.get("filename", "Unknown"),
                page=int(metadata.get("page_number", metadata.get("page", 0))),
                chunk_index=int(metadata.get("chunk_index", 0)),
                content=doc.page_content,
                relevance_score=float(1.0 - score),  # Convert distance to similarity score
                chunk_id=metadata.get("chunk_id", ""),
            )
            search_results.append(result)

        logger.info(f"ChromaDB search found {len(search_results)} results for query: '{query}'")
        return search_results

    except Exception as e:
        logger.error(f"ChromaDB search error: {e}")
        return []


@tool
def list_available_documents() -> List[Dict[str, Any]]:
    """
    List all available documents in the database with statistics.
    Returns:
        List of document information including filename, pages, and chunks
    """
    vectorstore = _get_vectorstore()
    if not vectorstore:
        return []
    try:
        # Get a sample of documents to analyze metadata
        sample_docs = vectorstore.similarity_search("document", k=100)  # Get larger sample

        # Organize by filename
        file_stats = {}
        for doc in sample_docs:
            metadata = doc.metadata
            filename = metadata.get("filename", "Unknown")
            page = metadata.get("page_number", metadata.get("page", 0))

            if filename not in file_stats:
                file_stats[filename] = {"pages": set(), "chunks": 0, "total_characters": 0}

            file_stats[filename]["pages"].add(page)
            file_stats[filename]["chunks"] += 1
            file_stats[filename]["total_characters"] += len(doc.page_content)

        # Convert to list format
        documents = []
        for filename, stats in file_stats.items():
            doc_info = {
                "filename": filename,
                "pages": len(stats["pages"]),
                "chunks": stats["chunks"],
                "total_characters": stats["total_characters"],
            }
            documents.append(doc_info)

        logger.info(f"Listed {len(documents)} available documents")
        return documents

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        return []


@tool(
    description="""Search within a specific document for relevant content.

IMPORTANT: When you use this tool to answer a question, you MUST:
1. Provide a comprehensive answer based on the retrieved content from the specified document

Args:
    filename: Name of the document to search in
    query: The search query string
    limit: Maximum number of results to return (default: 3)
Returns:
    List of relevant chunks from the specified document with page numbers for citation"""
)
def search_in_document(filename: str, query: str, limit: int = 3) -> List[SearchResult]:
    vectorstore = _get_vectorstore()
    if not vectorstore:
        return []
    try:
        # Get more results to filter by filename
        results_with_scores = vectorstore.similarity_search_with_score(query=query, k=20)

        # Filter results by filename and take top matches
        filtered_results = []
        for doc, score in results_with_scores:
            doc_filename = doc.metadata.get("filename", "")
            if filename.lower() in doc_filename.lower() or doc_filename.lower() in filename.lower():
                filtered_results.append((doc, score))
                if len(filtered_results) >= limit:
                    break

        search_results = []
        for doc, score in filtered_results:
            metadata = doc.metadata
            result = SearchResult(
                filename=metadata.get("filename", "Unknown"),
                page=int(metadata.get("page_number", metadata.get("page", 0))),
                chunk_index=int(metadata.get("chunk_index", 0)),
                content=doc.page_content,
                relevance_score=float(1.0 - score),  # Convert distance to similarity score
                chunk_id=metadata.get("chunk_id", ""),
            )
            search_results.append(result)

        logger.info(
            f"🔍 ChromaDB search found {len(search_results)} results in {filename} for query: '{query}'"
        )
        return search_results

    except Exception as e:
        logger.error(f"ChromaDB search error in document {filename}: {e}")
        return []


# Expose tools for LangGraph - UPDATED WITH INDIVIDUAL SQL TOOLS
TOOLS: List[Callable[..., Any]] = [
    search_documents,
    list_available_documents,
    search_in_document,
] + INDIVIDUAL_SQL_TOOLS  # Individual SQL tools for specific query types


def get_vectorstore() -> Optional[Chroma]:
    """
    Get the ChromaDB vectorstore instance.

    Returns:
        ChromaDB vectorstore instance or None if not available
    """
    return _get_vectorstore()


def get_collection_stats() -> Dict[str, Any]:
    """
    Get statistics about the ChromaDB collection.

    Returns:
        Dictionary containing collection statistics
    """
    vectorstore = _get_vectorstore()
    if not vectorstore:
        return {"error": "ChromaDB not available"}

    try:
        collection = vectorstore._collection
        return {
            "collection_name": settings.CHROMA_COLLECTION_NAME,
            "total_documents": collection.count(),
            "embedding_model": settings.EMBEDDING_MODEL,
            "database_path": str(settings.CHROMA_DB_PATH),
        }
    except Exception as e:
        return {"error": f"Failed to get collection stats: {e}"}
