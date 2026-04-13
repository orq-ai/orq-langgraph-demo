"""Individual SQL tools for the Hybrid Data Agent.

Each tool maps to one typed query in `sql_schemas.QUERY_TEMPLATES`. The
LLM picks a tool by reading its description — it never writes SQL, never
sees table names, and never chooses a query_type directly. Parameters are
validated by `QueryParameters.validate()` before the executor binds them.
"""

import logging
from typing import Any, Callable, List

from langchain_core.tools import tool

from .simple_sql_executor import simple_sql_executor
from .sql_schemas import QueryParameters

logger = logging.getLogger(__name__)


@tool(
    description="""Get monthly order performance for a specific dish.

Use this tool when users ask about how a particular menu item is selling —
order volume, revenue, rating, delivery time — optionally filtered to a city.

Examples:
- "How is Margherita pizza performing in 2024?"
- "Show me Ramen Shoyu orders in Berlin"
- "Carbonara sales trend last year"
- "Falafel Wrap orders per month"

Parameters:
- dish_name: Name of the dish (e.g., "Margherita Pizza", "Ramen Shoyu", "Carbonara")
- year: Year to analyze (2024-2025, default: 2024)
- city: Optional city filter (e.g., "Berlin", "Milan", "Paris")
- limit: Maximum number of results (default: 20)"""
)
def get_orders_by_dish(dish_name: str, year: int = 2024, city: str = None, limit: int = 20) -> str:
    """Get monthly orders data for a specific dish."""
    params = QueryParameters(dish_name=dish_name, year=year, city=city, limit=limit)
    logger.info(f"Getting orders for dish: {dish_name}, year: {year}")
    return simple_sql_executor.execute_query("orders_by_dish", params)


@tool(
    description="""Get order performance in a specific country.

Use this tool when users ask how the delivery service is performing in a
particular country — total orders, revenue, ratings — optionally filtered
to a cuisine type.

Examples:
- "How is Germany performing in 2024?"
- "Orders in France last year"
- "Italian food performance in Spain"
- "Show me revenue in Netherlands"

Parameters:
- country: Name of the country (e.g., "Germany", "Italy", "France", "Spain")
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter (e.g., "Italian", "Japanese", "Indian")
- limit: Maximum number of results (default: 20)"""
)
def get_orders_by_country(
    country: str, year: int = 2024, cuisine: str = None, limit: int = 20
) -> str:
    """Get orders data for a specific country."""
    params = QueryParameters(country=country, year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting orders for country: {country}, year: {year}")
    return simple_sql_executor.execute_query("orders_by_country", params)


@tool(
    description="""Get order performance across a geographic region.

Use this tool when users ask about performance across a region or continent.
Uses pattern matching: "Europe" matches "Western Europe", "Southern Europe",
"Central Europe", etc.

Examples:
- "Western Europe orders in 2024"
- "How are we doing in Southern Europe?"
- "Compare cuisines across Europe"
- "European market performance"

Parameters:
- region: Name or fragment of the region (e.g., "Europe", "Western", "Southern")
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter (e.g., "Italian", "Japanese")
- limit: Maximum number of results (default: 20)"""
)
def get_orders_by_region(
    region: str, year: int = 2024, cuisine: str = None, limit: int = 20
) -> str:
    """Get orders data for a specific geographic region."""
    params = QueryParameters(region=region, year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting orders for region: {region}, year: {year}")
    return simple_sql_executor.execute_query("orders_by_region", params)


@tool(
    description="""Get monthly order trends and seasonality patterns by cuisine.

Use this tool when users ask about trends over time — which cuisines are
growing, which months see peaks, seasonality of the overall business.

Examples:
- "Monthly order trends in 2024"
- "How did orders change month by month?"
- "Italian food trends this year"
- "Show me the monthly order pattern"

Parameters:
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter (e.g., "Italian", "Japanese")
- limit: Maximum number of results (default: 20)"""
)
def get_order_trends(year: int = 2024, cuisine: str = None, limit: int = 20) -> str:
    """Get monthly order trends."""
    params = QueryParameters(year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting order trends for year: {year}")
    return simple_sql_executor.execute_query("order_trends", params)


@tool(
    description="""Get the top-performing dishes by order volume.

Use this tool when users ask about best-selling dishes, top menu items,
or dish rankings.

Examples:
- "What are the top 10 dishes in 2024?"
- "Top 5 dishes by orders"
- "Best-selling items this year"
- "Show me the most-ordered dishes"

Parameters:
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter (e.g., "Italian", "Japanese")
- limit: Number of top dishes to show (default: 10)"""
)
def get_top_dishes(year: int = 2024, cuisine: str = None, limit: int = 10) -> str:
    """Get top-performing dishes by order volume."""
    params = QueryParameters(year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting top dishes for year: {year}")
    return simple_sql_executor.execute_query("top_dishes", params)


@tool(
    description="""Analyze order performance aggregated by cuisine type.

Use this tool when users ask about which cuisines are performing best,
cuisine-level comparisons, or overall cuisine metrics.

Examples:
- "How are the different cuisines performing?"
- "Compare Italian vs Japanese orders"
- "Which cuisine has the best ratings?"
- "Cuisine-level breakdown"

Parameters:
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter to narrow to one type (default: all)
- limit: Maximum number of cuisines to show (default: 20)"""
)
def get_cuisine_analysis(year: int = 2024, cuisine: str = None, limit: int = 20) -> str:
    """Analyze orders by cuisine type."""
    params = QueryParameters(year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting cuisine analysis for year: {year}")
    return simple_sql_executor.execute_query("cuisine_analysis", params)


@tool(
    description="""Compare dishes served at a specific restaurant.

Use this tool when users want to see how different dishes from the same
restaurant compare — which are the hero items, which are underperforming.

Examples:
- "Which dishes sell best at Trattoria Marco?"
- "Compare dishes at Sushi Zen"
- "What's popular at Bombay House?"
- "Show me menu performance for Burger Avenue"

Parameters:
- restaurant: Name (or fragment) of the restaurant (e.g., "Trattoria Marco", "Sushi Zen")
- year: Year to analyze (2024-2025, default: 2024)
- limit: Maximum number of dishes to show (default: 20)"""
)
def compare_dishes_by_restaurant(restaurant: str, year: int = 2024, limit: int = 20) -> str:
    """Compare dishes served at a specific restaurant."""
    params = QueryParameters(restaurant=restaurant, year=year, limit=limit)
    logger.info(f"Comparing dishes at restaurant: {restaurant}, year: {year}")
    return simple_sql_executor.execute_query("dishes_by_restaurant", params)


@tool(
    description="""Get the top-performing cities by order volume.

Use this tool when users ask which cities are driving the most orders,
revenue rankings by city, or geographic performance breakdowns.

Examples:
- "Top cities by orders in 2024"
- "Which cities generate the most revenue?"
- "Best-performing markets"
- "City rankings by orders"

Parameters:
- year: Year to analyze (2024-2025, default: 2024)
- cuisine: Optional cuisine filter to narrow ranking to one type
- limit: Number of top cities to show (default: 10)"""
)
def get_top_cities_by_orders(year: int = 2024, cuisine: str = None, limit: int = 10) -> str:
    """Get top-performing cities by order volume."""
    params = QueryParameters(year=year, cuisine=cuisine, limit=limit)
    logger.info(f"Getting top cities by orders for year: {year}")
    return simple_sql_executor.execute_query("top_cities", params)


@tool(
    description="""Get monthly order trends for a specific cuisine.

Use this tool when users ask about trends over time for a particular
cuisine — month-by-month patterns, growth, seasonality.

Examples:
- "Monthly trend for Japanese food in 2024"
- "How did Italian orders change over the year?"
- "Indian cuisine monthly pattern"
- "Thai food trend this year"

Parameters:
- cuisine: Type of cuisine (e.g., "Italian", "Japanese", "Indian", "Thai")
- year: Year to analyze (2024-2025, default: 2024)
- limit: Maximum number of results (default: 20)"""
)
def get_cuisine_order_trends(cuisine: str, year: int = 2024, limit: int = 20) -> str:
    """Get monthly order trends for a specific cuisine."""
    params = QueryParameters(cuisine=cuisine, year=year, limit=limit)
    logger.info(f"Getting cuisine order trends for: {cuisine}, year: {year}")
    return simple_sql_executor.execute_query("cuisine_order_trends", params)


SQL_TOOLS: List[Callable[..., Any]] = [
    get_orders_by_dish,
    get_orders_by_country,
    get_orders_by_region,
    get_order_trends,
    get_top_dishes,
    get_cuisine_analysis,
    compare_dishes_by_restaurant,
    get_top_cities_by_orders,
    get_cuisine_order_trends,
]
