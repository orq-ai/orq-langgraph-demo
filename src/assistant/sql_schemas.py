"""SQL query templates and parameter validation for Toyota RAG Assistant.

This module contains the predefined SQL query templates and simple parameter validation
for secure database operations.
"""

from dataclasses import dataclass
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryParameters:
    """Simple parameter container for SQL queries with basic validation."""

    model_name: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    brand: Optional[str] = None
    powertrain: Optional[str] = None
    limit: Optional[int] = None

    def validate(self) -> bool:
        """Basic parameter validation."""
        if self.year and (self.year < 2020 or self.year > 2030):
            logger.warning(f"Invalid year: {self.year}")
            return False
        if self.month and (self.month < 1 or self.month > 12):
            logger.warning(f"Invalid month: {self.month}")
            return False
        if self.limit and (self.limit < 1 or self.limit > 1000):
            logger.warning(f"Invalid limit: {self.limit}")
            return False
        # Basic string validation
        if self.model_name and len(self.model_name) > 100:
            logger.warning(f"Model name too long: {len(self.model_name)}")
            return False
        if self.country and len(self.country) > 100:
            logger.warning(f"Country name too long: {len(self.country)}")
            return False
        return True


# SQL Query Templates - Parameterized and secure
QUERY_TEMPLATES = {
    "sales_by_model": """
        SELECT
            fs.year,
            fs.month,
            dm.model_name,
            dm.brand,
            dm.powertrain,
            dc.country,
            dc.region,
            SUM(fs.contracts) as total_sales
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        JOIN dim_country dc ON fs.country_code = dc.country_code
        WHERE dm.model_name LIKE ? AND fs.year = ?
        {country_filter}
        GROUP BY fs.year, fs.month, dm.model_name, dm.brand, dm.powertrain, dc.country, dc.region
        ORDER BY fs.year, fs.month, total_sales DESC
        LIMIT ?
    """,
    "sales_by_country": """
        SELECT
            dc.country,
            dc.region,
            dm.brand,
            dm.model_name,
            SUM(fs.contracts) as total_sales
        FROM fact_sales fs
        JOIN dim_country dc ON fs.country_code = dc.country_code
        JOIN dim_model dm ON fs.model_id = dm.model_id
        WHERE dc.country = ? AND fs.year = ?
        {brand_filter}
        GROUP BY dc.country, dc.region, dm.brand, dm.model_name
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "sales_by_region": """
        SELECT
            dc.region,
            dc.country,
            dm.brand,
            dm.model_name,
            SUM(fs.contracts) as total_sales
        FROM fact_sales fs
        JOIN dim_country dc ON fs.country_code = dc.country_code
        JOIN dim_model dm ON fs.model_id = dm.model_id
        WHERE dc.region LIKE ? AND fs.year = ?
        {brand_filter}
        GROUP BY dc.region, dc.country, dm.brand, dm.model_name
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "sales_trends": """
        SELECT
            fs.year,
            fs.month,
            dm.brand,
            SUM(fs.contracts) as total_sales,
            COUNT(DISTINCT dm.model_name) as model_count
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        WHERE fs.year = ?
        {brand_filter}
        GROUP BY fs.year, fs.month, dm.brand
        ORDER BY fs.year, fs.month
        LIMIT ?
    """,
    "top_performers": """
        SELECT
            dm.model_name,
            dm.brand,
            dm.powertrain,
            SUM(fs.contracts) as total_sales,
            COUNT(DISTINCT dc.country) as countries_sold
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        JOIN dim_country dc ON fs.country_code = dc.country_code
        WHERE fs.year = ?
        {brand_filter}
        GROUP BY dm.model_name, dm.brand, dm.powertrain
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "powertrain_analysis": """
        SELECT
            dm.powertrain,
            dm.brand,
            COUNT(DISTINCT dm.model_name) as model_count,
            SUM(fs.contracts) as total_sales,
            ROUND(AVG(fs.contracts), 2) as avg_monthly_sales,
            COUNT(DISTINCT dc.country) as countries_sold
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        JOIN dim_country dc ON fs.country_code = dc.country_code
        WHERE fs.year = ?
        {brand_filter}
        GROUP BY dm.powertrain, dm.brand
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "model_comparison": """
        SELECT
            dm.model_name,
            dm.brand,
            dm.powertrain,
            fs.year,
            fs.month,
            SUM(fs.contracts) as total_sales,
            COUNT(DISTINCT dc.country) as countries_sold
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        JOIN dim_country dc ON fs.country_code = dc.country_code
        WHERE fs.year = ? AND dm.brand = ?
        GROUP BY dm.model_name, dm.brand, dm.powertrain, fs.year, fs.month
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "top_countries": """
        SELECT
            dc.country,
            dc.region,
            dm.brand,
            SUM(fs.contracts) as total_sales,
            COUNT(DISTINCT dm.model_name) as models_sold
        FROM fact_sales fs
        JOIN dim_country dc ON fs.country_code = dc.country_code
        JOIN dim_model dm ON fs.model_id = dm.model_id
        WHERE fs.year = ?
        {brand_filter}
        GROUP BY dc.country, dc.region, dm.brand
        ORDER BY total_sales DESC
        LIMIT ?
    """,
    "powertrain_trends": """
        SELECT
            fs.year,
            fs.month,
            dm.powertrain,
            dm.brand,
            SUM(fs.contracts) as total_sales,
            COUNT(DISTINCT dm.model_name) as model_count
        FROM fact_sales fs
        JOIN dim_model dm ON fs.model_id = dm.model_id
        WHERE fs.year = ? AND dm.powertrain LIKE ?
        {brand_filter}
        GROUP BY fs.year, fs.month, dm.powertrain, dm.brand
        ORDER BY fs.year, fs.month
        LIMIT ?
    """,
}


def build_query_params(query_type: str, params: QueryParameters) -> List[Any]:
    """Build parameter list for specific query types."""

    # Set default values
    year = params.year or 2024
    limit = params.limit or 20

    param_builders = {
        "sales_by_model": lambda: [
            f"{params.model_name}%" if params.model_name else "%",
            year,
            limit,
        ],
        "sales_by_country": lambda: [params.country or "Germany", year, limit],
        "sales_by_region": lambda: [f"%{params.region or 'Europe'}%", year, limit],
        "sales_trends": lambda: [year, limit],
        "top_performers": lambda: [year, limit],
        "powertrain_analysis": lambda: [year, limit],
        "model_comparison": lambda: [year, params.brand or "Toyota", limit],
        "top_countries": lambda: [year, limit],
        "powertrain_trends": lambda: [
            year,
            f"{params.powertrain}%" if params.powertrain else "%",
            limit,
        ],
    }

    return param_builders.get(query_type, lambda: [])()


def build_query_with_filters(query_type: str, params: QueryParameters) -> str:
    """Build query with optional filters applied."""
    base_query = QUERY_TEMPLATES.get(query_type, "")

    # Handle optional filters
    country_filter = ""
    brand_filter = ""

    if query_type in ["sales_by_model"] and params.country:
        country_filter = "AND dc.country = ?"

    if (
        query_type
        in [
            "sales_by_country",
            "sales_by_region",
            "sales_trends",
            "top_performers",
            "powertrain_analysis",
            "top_countries",
            "powertrain_trends",
        ]
        and params.brand
    ):
        brand_filter = "AND dm.brand = ?"

    # Format the query with filters
    formatted_query = base_query.format(country_filter=country_filter, brand_filter=brand_filter)

    return formatted_query


def build_final_params(query_type: str, params: QueryParameters) -> List[Any]:
    """Build final parameter list including optional filter parameters."""
    base_params = build_query_params(query_type, params)

    # Add additional parameters for filters
    if query_type == "sales_by_model" and params.country:
        # Insert country parameter before limit
        base_params.insert(-1, params.country)

    elif (
        query_type
        in [
            "sales_by_country",
            "sales_by_region",
            "sales_trends",
            "top_performers",
            "powertrain_analysis",
            "top_countries",
            "powertrain_trends",
        ]
        and params.brand
    ):
        # Insert brand parameter before limit
        base_params.insert(-1, params.brand)

    return base_params


# Available query types for documentation
AVAILABLE_QUERY_TYPES = list(QUERY_TEMPLATES.keys())
