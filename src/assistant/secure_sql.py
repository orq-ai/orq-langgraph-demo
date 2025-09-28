"""Secure SQL execution system with parameterized queries for Toyota RAG Assistant.

This module provides a secure interface for SQL operations using predefined query templates
and parameterized execution to prevent SQL injection attacks.
"""

from dataclasses import dataclass
from enum import Enum
import logging
import sqlite3
from typing import Any, Dict, List, Optional

import pandas as pd

from core.settings import settings

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Approved query types for the Toyota RAG system."""

    SALES_BY_MODEL = "sales_by_model"
    SALES_BY_COUNTRY = "sales_by_country"
    SALES_BY_REGION = "sales_by_region"
    SALES_TREND = "sales_trend"
    MODEL_COMPARISON = "model_comparison"
    POWERTRAIN_ANALYSIS = "powertrain_analysis"
    TOP_PERFORMERS = "top_performers"
    SCHEMA_INFO = "schema_info"


@dataclass
class QueryParameters:
    """Safe parameter container for SQL queries."""

    model_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    brand: Optional[str] = None
    powertrain: Optional[str] = None
    limit: Optional[int] = None
    comparison_type: Optional[str] = None
    time_period: Optional[str] = None

    def validate(self) -> bool:
        """Validate parameters against safe patterns."""
        if self.year and (self.year < 2020 or self.year > 2030):
            logger.warning(f"Invalid year: {self.year}")
            return False
        if self.month and (self.month < 1 or self.month > 12):
            logger.warning(f"Invalid month: {self.month}")
            return False
        if self.limit and (self.limit < 1 or self.limit > 1000):
            logger.warning(f"Invalid limit: {self.limit}")
            return False
        return True


class SecureSQLExecutor:
    """Secure SQL executor with parameterized queries."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.query_templates = self._init_query_templates()

    def _init_query_templates(self) -> Dict[QueryType, str]:
        """Initialize secure query templates with parameterized placeholders."""
        return {
            QueryType.SALES_BY_MODEL: """
                SELECT
                    fs.year,
                    fs.month,
                    dm.model_name,
                    dm.brand,
                    dm.powertrain,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE dm.model_name LIKE ? AND fs.year = ?
                GROUP BY fs.year, fs.month, dm.model_name, dm.brand, dm.powertrain
                ORDER BY fs.year, fs.month
                LIMIT ?
            """,
            QueryType.SALES_BY_COUNTRY: """
                SELECT
                    dc.country,
                    dc.region,
                    dm.brand,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_country dc ON fs.country_code = dc.country_code
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE dc.country = ? AND fs.year = ?
                GROUP BY dc.country, dc.region, dm.brand
                ORDER BY total_sales DESC
                LIMIT ?
            """,
            QueryType.SALES_BY_REGION: """
                SELECT
                    dc.region,
                    dc.country,
                    dm.brand,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_country dc ON fs.country_code = dc.country_code
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE dc.region = ? AND fs.year = ?
                GROUP BY dc.region, dc.country, dm.brand
                ORDER BY total_sales DESC
                LIMIT ?
            """,
            QueryType.SALES_TREND: """
                SELECT
                    fs.year,
                    fs.month,
                    dm.brand,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE fs.year = ?
                GROUP BY fs.year, fs.month, dm.brand
                ORDER BY fs.year, fs.month
                LIMIT ?
            """,
            QueryType.POWERTRAIN_ANALYSIS: """
                SELECT
                    dm.powertrain,
                    dm.brand,
                    COUNT(DISTINCT dm.model_name) as model_count,
                    SUM(fs.contracts) as total_sales,
                    ROUND(AVG(fs.contracts), 2) as avg_monthly_sales
                FROM fact_sales fs
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE fs.year = ?
                GROUP BY dm.powertrain, dm.brand
                ORDER BY total_sales DESC
                LIMIT ?
            """,
            QueryType.TOP_PERFORMERS: """
                SELECT
                    dm.model_name,
                    dm.brand,
                    dm.powertrain,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE fs.year = ?
                GROUP BY dm.model_name, dm.brand, dm.powertrain
                ORDER BY total_sales DESC
                LIMIT ?
            """,
            QueryType.MODEL_COMPARISON: """
                SELECT
                    dm.model_name,
                    dm.brand,
                    dm.powertrain,
                    fs.year,
                    SUM(fs.contracts) as total_sales
                FROM fact_sales fs
                JOIN dim_model dm ON fs.model_id = dm.model_id
                WHERE fs.year = ? AND dm.brand = ?
                GROUP BY dm.model_name, dm.brand, dm.powertrain, fs.year
                ORDER BY total_sales DESC
                LIMIT ?
            """,
            QueryType.SCHEMA_INFO: """
                SELECT
                    name as table_name,
                    type as object_type,
                    CASE
                        WHEN sql IS NOT NULL THEN 'Custom Table'
                        ELSE 'System Table'
                    END as description
                FROM sqlite_master
                WHERE type IN ('table', 'view')
                AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """,
        }

    def execute_secure_query(self, query_type: QueryType, params: QueryParameters) -> str:
        """Execute a secure parameterized query."""

        # Validate parameters first
        if not params.validate():
            return "Error: Invalid parameters provided"

        # Get query template
        if query_type not in self.query_templates:
            return "Error: Query type not supported"

        template = self.query_templates[query_type]

        try:
            # Build parameter list based on query type
            param_values = self._build_parameters(query_type, params)

            # Execute the query in a thread to avoid blocking the event loop
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._execute_query_sync, template, param_values)
                df = future.result(timeout=30)

            # Log successful execution
            logger.info(
                f"Executed secure query: {query_type.value} with {len(param_values)} parameters"
            )

            # Return formatted results
            if df.empty:
                return "No results found for the specified criteria."

            return df.to_string(index=False, max_rows=100)

        except Exception as e:
            logger.error(f"Secure query execution failed: {e}")
            return "Query execution error: Unable to process request safely"

    def _build_parameters(self, query_type: QueryType, params: QueryParameters) -> List[Any]:
        """Build parameter list for specific query types."""

        # Set default limit if not specified
        limit = params.limit or 20

        default_year = 2024
        default_country = "Germany"
        default_region = "Europe"
        default_brand = "Toyota"

        param_map = {
            QueryType.SALES_BY_MODEL: [
                f"{params.model_name}%" if params.model_name else "%",
                params.year or default_year,
                limit,
            ],
            QueryType.SALES_BY_COUNTRY: [
                params.country or default_country,  # Default country
                params.year or default_year,
                limit,
            ],
            QueryType.SALES_BY_REGION: [
                params.region or default_region,  # Default region
                params.year or default_year,
                limit,
            ],
            QueryType.SALES_TREND: [params.year or default_year, limit],
            QueryType.POWERTRAIN_ANALYSIS: [params.year or default_year, limit],
            QueryType.TOP_PERFORMERS: [params.year or default_year, limit],
            QueryType.MODEL_COMPARISON: [
                params.year or default_year,
                params.brand or default_brand,
                limit,
            ],
            QueryType.SCHEMA_INFO: [],  # No parameters needed
        }

        return param_map.get(query_type, [])

    def _execute_query_sync(self, template: str, param_values: List[Any]) -> pd.DataFrame:
        """Synchronous query execution helper for async operations."""
        conn = self._get_connection()
        if not conn:
            raise Exception("Could not connect to database")

        try:
            df = pd.read_sql_query(template, conn, params=param_values)
            return df
        finally:
            conn.close()

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get secure database connection."""
        try:
            conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro", uri=True, check_same_thread=False, timeout=30.0
            )
            logger.debug(f"Created secure SQLite connection to {self.db_path}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            return None

    def get_available_query_types(self) -> List[str]:
        """Get list of available query types for documentation."""
        return [query_type.value for query_type in QueryType]

    def get_query_template(self, query_type: QueryType) -> str:
        """Get the SQL template for a specific query type (for debugging)."""
        return self.query_templates.get(query_type, "Template not found")


# Global instance for use in tools
secure_sql_executor = SecureSQLExecutor(str(settings.DEFAULT_SQLITE_PATH))
