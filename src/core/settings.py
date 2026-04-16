"""
Application settings and configuration management using Pydantic.

This module provides a centralized configuration system that loads settings
from environment variables with proper validation, type checking, and defaults.
"""

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with fallback defaults.

    This class uses Pydantic BaseSettings to automatically load configuration
    from environment variables, with proper type validation and documentation.
    """

    # API Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for accessing GPT models")

    # orq.ai Configuration
    ORQ_API_BASE: str = Field(
        default="https://api.orq.ai/v2",
        description="Base URL for the orq.ai REST API. Override for staging/self-hosted deployments.",
    )

    ORQ_PROJECT_NAME: str = Field(
        default="Default",
        description="orq.ai project name for organizing datasets, experiments, and evaluators",
    )

    ORQ_KNOWLEDGE_BASE_ID: str = Field(
        default="",
        description="orq.ai Knowledge Base ID for document search (leave empty to create one on ingestion)",
    )

    ORQ_SYSTEM_PROMPT_ID: str = Field(
        default="",
        description="orq.ai prompt ID for the main system prompt (leave empty to use the local fallback in prompts.py)",
    )

    ORQ_SYSTEM_PROMPT_ID_VARIANT_B: str = Field(
        default="",
        description="orq.ai prompt ID for the 'variant B' system prompt used by `make evals-compare-prompts`",
    )

    ORQ_SAFETY_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the input-safety guardrail (falls back to OpenAI moderation if empty)",
    )

    ORQ_SOURCE_CITATIONS_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the source-citations Python evaluator used in the eval pipeline",
    )

    ORQ_GROUNDING_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the response-grounding LLM evaluator (checks every claim is in retrievals)",
    )

    ORQ_HALLUCINATION_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the hallucination-check LLM evaluator (checks for contradictions vs retrievals)",
    )

    ORQ_TRACING_BACKEND: Literal["callback", "otel", "none"] = Field(
        default="callback",
        description="Tracing backend: 'callback' (orq_ai_sdk.langchain handler, default), 'otel' (OpenTelemetry exporter), or 'none' (logging only). See LANGGRAPH-INTEGRATION.md for the tradeoffs.",
    )

    # Model Configuration
    DEFAULT_MODEL: str = Field(
        default="openai/gpt-4.1-mini",
        description="Default language model to use for AI operations",
    )

    JUDGE_MODEL: str = Field(
        default="openai/gpt-4.1-mini",
        description="Default language model to use as LLM-as-a-Judge operations",
    )

    MAX_SEARCH_RESULTS: int = Field(
        default=10,
        description="Maximum number of search results to return",
    )

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model used by orq.ai Knowledge Base",
    )

    # Data Ingestion Configuration
    CHUNK_SIZE: int = Field(
        default=1000,
        description="Maximum characters per text chunk for document processing",
    )

    CHUNK_OVERLAP: int = Field(
        default=200,
        description="Overlap between chunks for context preservation",
    )

    INPUT_DOCS_PATH: Path = Field(
        default=Path("./docs"),
        description="Default path to input documents directory",
    )

    DEFAULT_SQLITE_PATH: Path = Field(
        default=Path("./delivery_orders.db"),
        description="Default path for SQLite database",
    )

    # UI Configuration
    STARTERS_CSV_PATH: Path = Field(
        default=Path("./resources/conversation_starters.csv"),
        description="Path to CSV file containing conversation starters",
    )

    DEBUG: bool = Field(default=False, description="Enable debug mode")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host address")

    PORT: int = Field(default=8000, description="Server port number")

    # Validators
    @field_validator(
        "DEFAULT_SQLITE_PATH",
        "STARTERS_CSV_PATH",
        "INPUT_DOCS_PATH",
        mode="before",
    )
    @classmethod
    def convert_path_strings(cls, value):
        """Convert string paths to Path objects."""
        if isinstance(value, str):
            return Path(value)
        return value

    @field_validator("CHUNK_SIZE")
    @classmethod
    def validate_chunk_size(cls, value):
        """Validate chunk size is reasonable."""
        if value <= 0:
            raise ValueError("CHUNK_SIZE must be positive")
        if value < 100:
            raise ValueError("CHUNK_SIZE should be at least 100 characters")
        return value

    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_overlap(cls, value):
        """Validate chunk overlap is reasonable."""
        if value < 0:
            raise ValueError("CHUNK_OVERLAP must be non-negative")
        return value

    model_config = {
        "env_file": ".env",
        "extra": "allow",  # Allow extra fields that aren't explicitly defined here
    }


# Global settings instance
settings = Settings()
