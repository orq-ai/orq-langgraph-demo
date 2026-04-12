"""Simplified secure SQL executor for the Hybrid Data Agent.

This module provides a simple, secure interface for executing predefined SQL queries
with parameterized execution to prevent SQL injection attacks.
"""

import concurrent.futures
import logging
import sqlite3
from typing import Optional

import pandas as pd

from core.settings import settings

from .sql_schemas import (
    AVAILABLE_QUERY_TYPES,
    QueryParameters,
    build_final_params,
    build_query_with_filters,
)

logger = logging.getLogger(__name__)


class SimpleSQLExecutor:
    """Secure SQL executor with parameterized queries."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def execute_query(self, query_type: str, params: QueryParameters) -> str:
        """Execute a secure parameterized query."""

        # Validate parameters
        if not params.validate():
            return "Error: Invalid parameters provided"

        # Check if query type is supported
        if query_type not in AVAILABLE_QUERY_TYPES:
            return f"Error: Query type '{query_type}' not supported"

        try:
            # Build the query with filters
            query = build_query_with_filters(query_type, params)

            # Build parameter values
            param_values = build_final_params(query_type, params)

            # Execute the query in a thread to avoid blocking
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._execute_query_sync, query, param_values)
                df = future.result(timeout=30)

            # Log successful execution
            logger.info(f"Executed query: {query_type} with {len(param_values)} parameters")

            # Return formatted results
            if df.empty:
                return "No results found for the specified criteria."

            return df.to_string(index=False, max_rows=100)

        except Exception as e:
            logger.error(f"Query execution failed for {query_type}: {e}")
            return f"Query execution error: {str(e)}"

    def _execute_query_sync(self, query: str, param_values: list) -> pd.DataFrame:
        """Synchronous query execution helper."""
        conn = self._get_connection()
        if not conn:
            raise Exception("Could not connect to database")

        try:
            df = pd.read_sql_query(query, conn, params=param_values)
            return df
        finally:
            conn.close()

    def _get_connection(self) -> Optional[sqlite3.Connection]:
        """Get secure read-only database connection."""
        try:
            conn = sqlite3.connect(
                f"file:{self.db_path}?mode=ro", uri=True, check_same_thread=False, timeout=30.0
            )
            logger.debug(f"Created secure SQLite connection to {self.db_path}")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to SQLite: {e}")
            return None

    def get_available_query_types(self) -> list:
        """Get list of available query types."""
        return AVAILABLE_QUERY_TYPES.copy()


# Global instance for use in tools
simple_sql_executor = SimpleSQLExecutor(str(settings.DEFAULT_SQLITE_PATH))
