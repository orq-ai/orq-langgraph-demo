"""Individual SQL tools for the Hybrid Data Agent.

This module provides specific, well-documented tools for each type of sales data query.
Each tool maps directly to a specific SQL query template for better clarity and control.
"""

import logging
from typing import Any, Callable, List

from langchain_core.tools import tool

from .simple_sql_executor import simple_sql_executor
from .sql_schemas import QueryParameters

logger = logging.getLogger(__name__)


@tool(
    description="""Get sales data for a specific vehicle model.

Use this tool when users ask about sales performance of specific car models.

Examples:
- "How did RAV4 perform in 2024?"
- "Show me Camry sales in Germany"
- "What were Lexus ES sales last year?"
- "RAV4 sales in 2023"

Parameters:
- model_name: Name of the vehicle model (e.g., "RAV4", "Camry", "ES")
- year: Year to analyze (2020-2024, default: 2024)
- country: Optional country filter (e.g., "Germany", "France")
- limit: Maximum number of results (default: 20)"""
)
def get_sales_by_model(
    model_name: str, year: int = 2024, country: str = None, limit: int = 20
) -> str:
    """Get sales data for a specific vehicle model."""
    params = QueryParameters(model_name=model_name, year=year, country=country, limit=limit)

    logger.info(f"Getting sales data for model: {model_name}, year: {year}")
    return simple_sql_executor.execute_query("sales_by_model", params)


@tool(
    description="""Get sales data for a specific country.

Use this tool when users ask about sales performance in specific countries or markets.

Examples:
- "Toyota sales in Germany 2024"
- "How is Toyota performing in France?"
- "Show me Lexus sales in UK"
- "What are the sales numbers for Japan?"

Parameters:
- country: Name of the country (e.g., "Germany", "France", "Japan")
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Maximum number of results (default: 20)"""
)
def get_sales_by_country(country: str, year: int = 2024, brand: str = None, limit: int = 20) -> str:
    """Get sales data for a specific country."""
    params = QueryParameters(country=country, year=year, brand=brand, limit=limit)

    logger.info(f"Getting sales data for country: {country}, year: {year}")
    return simple_sql_executor.execute_query("sales_by_country", params)


@tool(
    description="""Get sales data for a specific geographic region.

Use this tool when users ask about sales performance across regions or continents.
The tool uses pattern matching, so "Europe" will match "Western Europe", "Eastern Europe", etc.

Examples:
- "Toyota sales in Europe 2024"
- "How is Lexus performing in Asia?"
- "Show me sales across North America"
- "European market performance"
- "Compare Lexus sales across European countries"

Parameters:
- region: Name of the region (e.g., "Europe", "Asia", "America"). Uses pattern matching.
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Maximum number of results (default: 20)"""
)
def get_sales_by_region(region: str, year: int = 2024, brand: str = None, limit: int = 20) -> str:
    """Get sales data for a specific region."""
    params = QueryParameters(region=region, year=year, brand=brand, limit=limit)

    logger.info(f"Getting sales data for region: {region}, year: {year}")
    return simple_sql_executor.execute_query("sales_by_region", params)


@tool(
    description="""Get monthly sales trends and patterns.

Use this tool when users ask about sales trends over time, seasonality, or monthly patterns.

Examples:
- "Show me monthly sales trends for 2024"
- "Toyota sales trends this year"
- "How did sales change month by month?"
- "Seasonal sales patterns for Lexus"

Parameters:
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Maximum number of results (default: 20)"""
)
def get_sales_trends(year: int = 2024, brand: str = None, limit: int = 20) -> str:
    """Get monthly sales trends."""
    params = QueryParameters(year=year, brand=brand, limit=limit)

    logger.info(f"Getting sales trends for year: {year}")
    return simple_sql_executor.execute_query("sales_trends", params)


@tool(
    description="""Get top performing models by sales volume.

Use this tool when users ask about best-selling models, top performers, or rankings.

Examples:
- "What are the top selling models in 2024?"
- "Show me the best performing Toyota models"
- "Top 10 Lexus models by sales"
- "Which models sold the most?"

Parameters:
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Number of top models to show (default: 10)"""
)
def get_top_performing_models(year: int = 2024, brand: str = None, limit: int = 10) -> str:
    """Get top performing models by sales volume."""
    params = QueryParameters(year=year, brand=brand, limit=limit)

    logger.info(f"Getting top performing models for year: {year}")
    return simple_sql_executor.execute_query("top_performers", params)


@tool(
    description="""Analyze sales performance by powertrain type (hybrid, gas, electric).

Use this tool when users ask about powertrain performance, electrification trends, or hybrid sales.

Examples:
- "How are hybrid vehicles performing?"
- "Electric vehicle sales in 2024"
- "Compare gas vs hybrid sales"
- "Powertrain analysis for Toyota"

Parameters:
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Maximum number of results (default: 20)"""
)
def get_powertrain_analysis(year: int = 2024, brand: str = None, limit: int = 20) -> str:
    """Analyze sales by powertrain type."""
    params = QueryParameters(year=year, brand=brand, limit=limit)

    logger.info(f"Getting powertrain analysis for year: {year}")
    return simple_sql_executor.execute_query("powertrain_analysis", params)


@tool(
    description="""Compare models within a specific brand.

Use this tool when users want to compare different models from Toyota or Lexus.

Examples:
- "Compare Toyota models in 2024"
- "Which Lexus models are selling best?"
- "Toyota model comparison"
- "Show me all Lexus model performance"

Parameters:
- brand: Brand to analyze ("Toyota" or "Lexus")
- year: Year to analyze (2020-2024, default: 2024)
- limit: Maximum number of models to show (default: 20)"""
)
def compare_models_by_brand(brand: str, year: int = 2024, limit: int = 20) -> str:
    """Compare models within a specific brand."""
    params = QueryParameters(brand=brand, year=year, limit=limit)

    logger.info(f"Comparing models for brand: {brand}, year: {year}")
    return simple_sql_executor.execute_query("model_comparison", params)


@tool(
    description="""Get top performing countries by sales volume.

Use this tool when users ask about which countries have the highest sales or country rankings.

Examples:
- "Top countries by vehicle sales"
- "Which countries buy the most Toyotas?"
- "Best performing markets"
- "Country sales rankings"

Parameters:
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Number of top countries to show (default: 10)"""
)
def get_top_countries_by_sales(year: int = 2024, brand: str = None, limit: int = 10) -> str:
    """Get top performing countries by sales volume."""
    params = QueryParameters(year=year, brand=brand, limit=limit)

    logger.info(f"Getting top countries by sales for year: {year}")
    return simple_sql_executor.execute_query("top_countries", params)


@tool(
    description="""Get sales trends for specific powertrain types over time.

Use this tool when users ask about trends for hybrid, electric, or gas vehicles over months.

Examples:
- "Monthly sales trends for hybrid vehicles"
- "Electric vehicle trends in 2024"
- "How did hybrid sales change over the year?"
- "Gas vehicle sales patterns"

Parameters:
- powertrain: Type of powertrain (e.g., "Hybrid", "Gas", "Electric")
- year: Year to analyze (2020-2024, default: 2024)
- brand: Optional brand filter ("Toyota" or "Lexus")
- limit: Maximum number of results (default: 20)"""
)
def get_powertrain_sales_trends(
    powertrain: str, year: int = 2024, brand: str = None, limit: int = 20
) -> str:
    """Get sales trends for specific powertrain types."""
    params = QueryParameters(powertrain=powertrain, year=year, brand=brand, limit=limit)

    logger.info(f"Getting powertrain trends for: {powertrain}, year: {year}")
    return simple_sql_executor.execute_query("powertrain_trends", params)


# List of all individual SQL tools
INDIVIDUAL_SQL_TOOLS: List[Callable[..., Any]] = [
    get_sales_by_model,
    get_sales_by_country,
    get_sales_by_region,
    get_sales_trends,
    get_top_performing_models,
    get_powertrain_analysis,
    compare_models_by_brand,
    get_top_countries_by_sales,
    get_powertrain_sales_trends,
]
