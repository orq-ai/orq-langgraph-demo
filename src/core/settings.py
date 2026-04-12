"""
Application settings and configuration management using Pydantic.

This module provides a centralized configuration system that loads settings
from environment variables with proper validation, type checking, and defaults.
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables with fallback defaults.

    This class uses Pydantic BaseSettings to automatically load configuration
    from environment variables, with proper type validation and documentation.
    """

    # API Configuration
    OPENAI_API_KEY: str = Field(
        ..., description="OpenAI API key for accessing GPT models", env="OPENAI_API_KEY"
    )

    # orq.ai Configuration
    ORQ_PROJECT_NAME: str = Field(
        default="Default",
        description="orq.ai project name for organizing datasets, experiments, and evaluators",
        env="ORQ_PROJECT_NAME",
    )

    ORQ_KNOWLEDGE_BASE_ID: str = Field(
        default="",
        description="orq.ai Knowledge Base ID for document search (leave empty to create one on ingestion)",
        env="ORQ_KNOWLEDGE_BASE_ID",
    )

    ORQ_SYSTEM_PROMPT_ID: str = Field(
        default="",
        description="orq.ai prompt ID for the main system prompt (leave empty to use the local fallback in prompts.py)",
        env="ORQ_SYSTEM_PROMPT_ID",
    )

    ORQ_SYSTEM_PROMPT_ID_VARIANT_B: str = Field(
        default="",
        description="orq.ai prompt ID for the 'variant B' system prompt used by `make evals-compare-prompts`",
        env="ORQ_SYSTEM_PROMPT_ID_VARIANT_B",
    )

    ORQ_SAFETY_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the input-safety guardrail (falls back to OpenAI moderation if empty)",
        env="ORQ_SAFETY_EVALUATOR_ID",
    )

    ORQ_SOURCE_CITATIONS_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the source-citations Python evaluator used in the eval pipeline",
        env="ORQ_SOURCE_CITATIONS_EVALUATOR_ID",
    )

    ORQ_GROUNDING_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the response-grounding LLM evaluator (checks every claim is in retrievals)",
        env="ORQ_GROUNDING_EVALUATOR_ID",
    )

    ORQ_HALLUCINATION_EVALUATOR_ID: str = Field(
        default="",
        description="orq.ai evaluator ID for the hallucination-check LLM evaluator (checks for contradictions vs retrievals)",
        env="ORQ_HALLUCINATION_EVALUATOR_ID",
    )

    # Model Configuration
    DEFAULT_MODEL: str = Field(
        default="openai/gpt-4.1-mini",
        description="Default language model to use for AI operations",
        env="DEFAULT_MODEL",
    )

    JUDGE_MODEL: str = Field(
        default="openai/gpt-4.1-mini",
        description="Default language model to use as LLM-as-a-Judge operations",
        env="JUDGE_MODEL",
    )

    MAX_SEARCH_RESULTS: int = Field(
        default=10,
        description="Maximum number of search results to return",
        env="MAX_SEARCH_RESULTS",
    )

    # Embedding Configuration
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model used by orq.ai Knowledge Base",
        env="EMBEDDING_MODEL",
    )

    # Data Ingestion Configuration
    CHUNK_SIZE: int = Field(
        default=1000,
        description="Maximum characters per text chunk for document processing",
        env="CHUNK_SIZE",
    )

    CHUNK_OVERLAP: int = Field(
        default=200,
        description="Overlap between chunks for context preservation",
        env="CHUNK_OVERLAP",
    )

    INPUT_DOCS_PATH: Path = Field(
        default=Path("./docs"),
        description="Default path to input documents directory",
        env="INPUT_DOCS_PATH",
    )

    DEFAULT_SQLITE_PATH: Path = Field(
        default=Path("./toyota_sales.db"),
        description="Default path for SQLite database",
        env="DEFAULT_SQLITE_PATH",
    )

    # UI Configuration
    STARTERS_CSV_PATH: Path = Field(
        default=Path("./resources/converstation_starters.csv"),
        description="Path to CSV file containing conversation starters",
        env="STARTERS_CSV_PATH",
    )

    DEBUG: bool = Field(default=False, description="Enable debug mode", env="DEBUG")

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host address", env="HOST")

    PORT: int = Field(default=8000, description="Server port number", env="PORT")

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
