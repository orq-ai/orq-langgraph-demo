#!/usr/bin/env python3
"""
PDF Document Ingestion Pipeline for orq.ai Knowledge Base.

Pipeline for ingesting PDF documents into an orq.ai Knowledge Base with:
- Semantic-aware local chunking (PyPDFLoader + RecursiveCharacterTextSplitter)
- Rich metadata extraction
- Batch chunk upload via orq.ai SDK
- Verification via orq.ai search API

Features chosen for the sake of simplicity and time constraints for the PoC.
For a production environment, consider adding:
    - Contextual Retrieval
    - Metadata enrichment
    - Summarization
    - Document deduplication
"""

from datetime import datetime
import hashlib
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple
import warnings

import httpx
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from orq_ai_sdk import Orq

# Add src directory to path for importing settings
sys.path.append(str(Path(__file__).parent.parent / "src"))
from core.settings import settings

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("orq_ingestion.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Ignore PyPDF warnings about deprecated features
warnings.filterwarnings("ignore", category=UserWarning, module="pypdf._reader")


class OrqPDFIngestionPipeline:
    """PDF ingestion pipeline for orq.ai Knowledge Base."""

    def __init__(
        self,
        knowledge_base_id: Optional[str] = None,
        knowledge_base_key: str = "hybrid-data-agent-kb",
        embedding_model: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        orq_api_key: Optional[str] = None,
        project_path: Optional[str] = None,
    ):
        """
        Initialize the orq.ai Knowledge Base ingestion pipeline.

        Args:
            knowledge_base_id: Existing Knowledge Base ID. If None, a new KB is created.
            knowledge_base_key: Key/name for the Knowledge Base (used when creating).
            embedding_model: Embedding model for the KB (e.g. "openai/text-embedding-3-small").
            chunk_size: Max characters per chunk (uses settings default if None).
            chunk_overlap: Overlap between chunks (uses settings default if None).
            orq_api_key: orq.ai API key (uses ORQ_API_KEY env var if not provided).
            project_path: orq.ai project path (uses settings.ORQ_PROJECT_NAME if None).
        """
        self.orq_api_key = orq_api_key or os.environ.get("ORQ_API_KEY")
        if not self.orq_api_key:
            raise ValueError("ORQ_API_KEY is required. Set it in the environment.")

        self.knowledge_base_key = knowledge_base_key
        self.embedding_model = embedding_model or f"openai/{settings.EMBEDDING_MODEL}"
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.project_path = project_path or settings.ORQ_PROJECT_NAME

        self.client = Orq(api_key=self.orq_api_key)

        self._setup_text_splitter()
        self.knowledge_base_id = knowledge_base_id or self._create_knowledge_base()
        logger.info(f"Using Knowledge Base ID: {self.knowledge_base_id}")

    def _create_knowledge_base(self) -> str:
        """Find an existing Knowledge Base by key or create a new one.

        Uses raw HTTP because the installed SDK's CreateKnowledgeRequestBody
        is missing the required `type` field that the API demands.
        """
        # First, check if a KB with this key already exists
        existing_id = self._find_knowledge_base_by_key(self.knowledge_base_key)
        if existing_id:
            logger.info(
                f"Reusing existing Knowledge Base '{self.knowledge_base_key}' ({existing_id})"
            )
            return existing_id

        logger.info(
            f"Creating Knowledge Base '{self.knowledge_base_key}' "
            f"in project '{self.project_path}' with embedding model '{self.embedding_model}'"
        )
        headers = {
            "Authorization": f"Bearer {self.orq_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "key": self.knowledge_base_key,
            "embedding_model": self.embedding_model,
            "path": self.project_path,
            "type": "internal",
        }
        response = httpx.post(
            "https://api.orq.ai/v2/knowledge",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Failed to create Knowledge Base (status {response.status_code}): {response.text}"
            )
        body = response.json()
        kb_id = body.get("_id") or body.get("id")
        if not kb_id:
            raise RuntimeError(f"Could not extract KB ID from response: {body}")
        return kb_id

    def _find_knowledge_base_by_key(self, key: str) -> Optional[str]:
        """Return the ID of an existing Knowledge Base with this key, or None."""
        try:
            response = self.client.knowledge.list(limit=50)
            items = getattr(response, "data", []) or []
            for kb in items:
                if getattr(kb, "key", None) == key:
                    return getattr(kb, "id", None) or getattr(kb, "_id", None)
        except Exception as e:
            logger.warning(f"Failed to list existing Knowledge Bases: {e}")
        return None

    def _setup_text_splitter(self) -> None:
        """Initialize text splitter with semantic-aware settings."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=[
                "\n\n",
                "\n",
                ". ",
                "! ",
                "? ",
                "; ",
                ", ",
                " ",
                "",
            ],
            length_function=len,
            is_separator_regex=False,
        )
        logger.info(
            f"Text splitter configured - Chunk size: {self.chunk_size}, Overlap: {self.chunk_overlap}"
        )

    def _extract_pdf_metadata(self, file_path: str, document: Document) -> Dict[str, Any]:
        """Extract metadata from PDF file and document."""
        file_stat = os.stat(file_path)
        file_hash = self._calculate_file_hash(file_path)

        metadata: Dict[str, Any] = {
            "source": file_path,
            "filename": os.path.basename(file_path),
            "file_size": file_stat.st_size,
            "file_hash": file_hash,
            "ingestion_timestamp": datetime.now().isoformat(),
            "document_type": "pdf",
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "embedding_model": self.embedding_model,
        }

        if hasattr(document, "metadata") and document.metadata:
            original_metadata = document.metadata
            metadata.update(
                {
                    "page_number": original_metadata.get("page", 0),
                    "total_pages": original_metadata.get("total_pages", 0),
                }
            )

        return metadata

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for deduplication."""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def _process_single_pdf(self, file_path: str) -> Tuple[List[Document], Dict[str, Any]]:
        """Process a single PDF file into chunks with metadata."""
        try:
            logger.info(f"Processing PDF: {file_path}")

            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents:
                raise ValueError(f"No content extracted from {file_path}")

            chunks = self.text_splitter.split_documents(documents)

            enhanced_chunks = []
            for i, chunk in enumerate(chunks):
                base_metadata = self._extract_pdf_metadata(file_path, chunk)
                chunk_metadata = {
                    **base_metadata,
                    "chunk_id": f"{base_metadata['file_hash']}_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "chunk_text_length": len(chunk.page_content),
                }
                chunk.metadata = chunk_metadata
                enhanced_chunks.append(chunk)

            processing_stats = {
                "filename": os.path.basename(file_path),
                "pages_processed": len(documents),
                "chunks_created": len(enhanced_chunks),
                "total_characters": sum(len(c.page_content) for c in enhanced_chunks),
                "status": "success",
            }

            logger.info(
                f"Successfully processed {file_path} - {len(enhanced_chunks)} chunks created"
            )
            return enhanced_chunks, processing_stats

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return [], {
                "filename": os.path.basename(file_path),
                "status": "error",
                "error_message": str(e),
            }

    def _upload_chunks(self, datasource_id: str, chunks: List[Document]) -> None:
        """
        Upload chunks to a datasource via REST API.

        Uses raw HTTP because the SDK's typed CreateChunkMetadata silently
        strips extra fields — we need to preserve all our custom metadata.
        """
        # orq.ai metadata values must be primitive (string, number, bool).
        # Flatten non-primitives to strings.
        def flatten_value(v: Any) -> Any:
            if isinstance(v, (str, int, float, bool)) or v is None:
                return v
            return str(v)

        payload = [
            {
                "text": chunk.page_content,
                "metadata": {k: flatten_value(v) for k, v in chunk.metadata.items()},
            }
            for chunk in chunks
        ]

        headers = {
            "Authorization": f"Bearer {self.orq_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = (
            f"https://api.orq.ai/v2/knowledge/{self.knowledge_base_id}"
            f"/datasources/{datasource_id}/chunks"
        )
        response = httpx.post(url, headers=headers, json=payload, timeout=120.0)
        response.raise_for_status()

    def ingest_pdf_directory(
        self, folder_path: str, file_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Ingest all PDF files from a directory into the Knowledge Base."""
        if file_patterns is None:
            file_patterns = ["*.pdf"]

        folder_path_obj = Path(folder_path)
        if not folder_path_obj.exists():
            raise ValueError(f"Directory does not exist: {folder_path}")

        pdf_files = []
        for pattern in file_patterns:
            pdf_files.extend(folder_path_obj.glob(pattern))

        if not pdf_files:
            logger.warning(f"No PDF files found in {folder_path}")
            return {"status": "no_files", "files_processed": 0}

        logger.info(f"Found {len(pdf_files)} PDF files to process")

        processing_results = []
        total_chunks_uploaded = 0

        for pdf_file in pdf_files:
            chunks, stats = self._process_single_pdf(str(pdf_file))
            processing_results.append(stats)

            if not chunks:
                continue

            # Create a datasource for this PDF
            filename = os.path.basename(str(pdf_file))
            try:
                datasource = self.client.knowledge.create_datasource(
                    knowledge_id=self.knowledge_base_id,
                    display_name=filename,
                )
                datasource_id = getattr(datasource, "id", None) or getattr(
                    datasource, "_id", None
                )
                if not datasource_id:
                    raise RuntimeError(f"Could not extract datasource ID from response: {datasource}")

                logger.info(f"Created datasource '{filename}' ({datasource_id})")
            except Exception as e:
                logger.error(f"Failed to create datasource for {filename}: {e}")
                stats["status"] = "error"
                stats["error_message"] = f"datasource creation failed: {e}"
                continue

            # Upload chunks in batches (orq.ai API limit: 100 chunks per request)
            batch_size = 100
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i : i + batch_size]
                try:
                    self._upload_chunks(datasource_id, batch)
                    total_chunks_uploaded += len(batch)
                    logger.info(
                        f"Uploaded batch {i // batch_size + 1} ({len(batch)} chunks) for {filename}"
                    )
                except Exception as e:
                    logger.error(f"Failed to upload batch for {filename}: {e}")
                    stats["status"] = "error"
                    stats["error_message"] = f"chunk upload failed: {e}"
                    break

        successful_files = [r for r in processing_results if r["status"] == "success"]
        failed_files = [r for r in processing_results if r["status"] == "error"]

        results = {
            "status": "completed",
            "knowledge_base_id": self.knowledge_base_id,
            "files_processed": len(pdf_files),
            "successful_files": len(successful_files),
            "failed_files": len(failed_files),
            "total_chunks": total_chunks_uploaded,
            "total_characters": sum(r.get("total_characters", 0) for r in successful_files),
            "processing_results": processing_results,
        }

        logger.info(
            f"Ingestion completed - {results['successful_files']}/{results['files_processed']} files successful"
        )
        return results

    def verify_ingestion(self, sample_queries: Optional[List[str]] = None) -> Dict[str, Any]:
        """Verify ingestion by performing test searches via orq.ai."""
        if sample_queries is None:
            sample_queries = [
                "Toyota",
                "warranty",
                "contract terms",
                "Lexus",
                "vehicle maintenance",
            ]

        verification_results: Dict[str, Any] = {"search_tests": []}

        for query in sample_queries:
            try:
                response = self.client.knowledge.search(
                    knowledge_id=self.knowledge_base_id,
                    query=query,
                )
                matches = getattr(response, "matches", None) or []
                sample_content = None
                if matches:
                    first = matches[0]
                    text = getattr(first, "text", None) or getattr(first, "content", None) or ""
                    sample_content = text[:200] + "..." if text else None

                verification_results["search_tests"].append(
                    {
                        "query": query,
                        "results_found": len(matches),
                        "status": "success",
                        "sample_content": sample_content,
                    }
                )
            except Exception as e:
                verification_results["search_tests"].append(
                    {"query": query, "status": "error", "error_message": str(e)}
                )

        return verification_results


def create_pipeline_from_settings() -> OrqPDFIngestionPipeline:
    """Create an OrqPDFIngestionPipeline using configuration from settings."""
    return OrqPDFIngestionPipeline(
        knowledge_base_id=settings.ORQ_KNOWLEDGE_BASE_ID or None,
        embedding_model=f"openai/{settings.EMBEDDING_MODEL}",
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )


def main():
    """Main function demonstrating the pipeline usage."""
    DOCS_FOLDER = str(settings.INPUT_DOCS_PATH)

    print("Configuration from settings:")
    print(f"  - Input docs path: {DOCS_FOLDER}")
    print(f"  - orq.ai project: {settings.ORQ_PROJECT_NAME}")
    print(f"  - Existing KB ID: {settings.ORQ_KNOWLEDGE_BASE_ID or '(will create new)'}")
    print(f"  - Embedding model: openai/{settings.EMBEDDING_MODEL}")
    print(f"  - Chunk size: {settings.CHUNK_SIZE}")
    print(f"  - Chunk overlap: {settings.CHUNK_OVERLAP}")
    print()

    try:
        pipeline = create_pipeline_from_settings()

        print("Starting PDF ingestion...")
        results = pipeline.ingest_pdf_directory(DOCS_FOLDER)

        print("\nIngestion Results:")
        print(f"  - Knowledge Base ID: {results['knowledge_base_id']}")
        print(f"  - Files processed: {results['files_processed']}")
        print(f"  - Successful files: {results['successful_files']}")
        print(f"  - Failed files: {results['failed_files']}")
        print(f"  - Total chunks uploaded: {results['total_chunks']}")
        print(f"  - Total characters: {results['total_characters']:,}")

        if not settings.ORQ_KNOWLEDGE_BASE_ID:
            print(
                f"\nTIP: set ORQ_KNOWLEDGE_BASE_ID={results['knowledge_base_id']} in .env "
                f"to reuse this Knowledge Base on subsequent runs."
            )

        print("\nVerifying ingestion...")
        verification = pipeline.verify_ingestion(
            [
                "Toyota warranty policy",
                "Lexus contract terms",
                "vehicle maintenance requirements",
                "warranty coverage period",
            ]
        )

        print("  - Search test results:")
        for test in verification["search_tests"]:
            status = "[ok]" if test["status"] == "success" else "[fail]"
            print(f"    {status} '{test['query']}': {test.get('results_found', 0)} results")

        print("\nPipeline completed successfully!")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        print(f"\nPipeline failed: {e}")
        raise


if __name__ == "__main__":
    main()
