"""SQL query templates and parameter validation for the Hybrid Data Agent.

This module contains the predefined SQL query templates and simple parameter
validation for secure database operations against the food-delivery schema:

    fact_orders       one row per (restaurant, dish, month) with aggregates
                      orders_count, revenue_eur, avg_rating, avg_delivery_minutes
    dim_dish          dish_id, dish_name, cuisine, category, base_price_eur,
                      calories, allergens
    dim_restaurant    restaurant_id, restaurant_name, city_id, cuisine_type, avg_rating
    dim_city          city_id, city_name, country, region

The queries are parameterized and never string-interpolate user input —
the LLM picks a `query_type` and passes validated `QueryParameters`, and
the executor binds the values via sqlite3 placeholders. Adding a new query
type is a matter of adding an entry to `QUERY_TEMPLATES` + a corresponding
builder in `build_query_params` — no changes to the agent code.
"""

from dataclasses import dataclass
import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class QueryParameters:
    """Parameter container for SQL queries with basic validation.

    Every field is optional so the same dataclass can serve any of the
    9 query types. The executor's `build_query_params` / `build_final_params`
    decides which fields each query type actually consumes.
    """

    dish_name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    restaurant: Optional[str] = None
    cuisine: Optional[str] = None
    category: Optional[str] = None
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
        # Length caps — cheap defense against injection-length abuse.
        for name, value in (
            ("dish_name", self.dish_name),
            ("city", self.city),
            ("country", self.country),
            ("region", self.region),
            ("restaurant", self.restaurant),
            ("cuisine", self.cuisine),
            ("category", self.category),
        ):
            if value and len(value) > 100:
                logger.warning(f"{name} too long: {len(value)}")
                return False
        return True


# SQL Query Templates — parameterized and secure.
#
# Every query groups fact_orders at (year, month, …) and exposes the four
# numeric aggregates the tools care about:
#   - total_orders           SUM(orders_count)
#   - total_revenue_eur      SUM(revenue_eur)
#   - avg_rating             AVG(avg_rating)    weighted by orders_count
#   - avg_delivery_minutes   AVG(avg_delivery_minutes)
QUERY_TEMPLATES = {
    "orders_by_dish": """
        SELECT
            fo.year,
            fo.month,
            dd.dish_name,
            dd.cuisine,
            dd.category,
            dc.city_name,
            dc.country,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating,
            ROUND(AVG(fo.avg_delivery_minutes), 1) AS avg_delivery_minutes
        FROM fact_orders fo
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        JOIN dim_city dc ON fo.city_id = dc.city_id
        WHERE dd.dish_name LIKE ? AND fo.year = ?
        {city_filter}
        GROUP BY fo.year, fo.month, dd.dish_name, dd.cuisine, dd.category, dc.city_name, dc.country
        ORDER BY fo.year, fo.month, total_orders DESC
        LIMIT ?
    """,
    "orders_by_country": """
        SELECT
            dc.country,
            dc.region,
            dd.cuisine,
            dd.dish_name,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating
        FROM fact_orders fo
        JOIN dim_city dc ON fo.city_id = dc.city_id
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE dc.country = ? AND fo.year = ?
        {cuisine_filter}
        GROUP BY dc.country, dc.region, dd.cuisine, dd.dish_name
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "orders_by_region": """
        SELECT
            dc.region,
            dc.country,
            dd.cuisine,
            dd.dish_name,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur
        FROM fact_orders fo
        JOIN dim_city dc ON fo.city_id = dc.city_id
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE dc.region LIKE ? AND fo.year = ?
        {cuisine_filter}
        GROUP BY dc.region, dc.country, dd.cuisine, dd.dish_name
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "order_trends": """
        SELECT
            fo.year,
            fo.month,
            dd.cuisine,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            COUNT(DISTINCT dd.dish_name) AS dish_count
        FROM fact_orders fo
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE fo.year = ?
        {cuisine_filter}
        GROUP BY fo.year, fo.month, dd.cuisine
        ORDER BY fo.year, fo.month
        LIMIT ?
    """,
    "top_dishes": """
        SELECT
            dd.dish_name,
            dd.cuisine,
            dd.category,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating,
            COUNT(DISTINCT dc.city_name) AS cities_sold
        FROM fact_orders fo
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        JOIN dim_city dc ON fo.city_id = dc.city_id
        WHERE fo.year = ?
        {cuisine_filter}
        GROUP BY dd.dish_name, dd.cuisine, dd.category
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "cuisine_analysis": """
        SELECT
            dd.cuisine,
            COUNT(DISTINCT dd.dish_name) AS dish_count,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating,
            ROUND(AVG(fo.avg_delivery_minutes), 1) AS avg_delivery_minutes,
            COUNT(DISTINCT dc.city_name) AS cities_sold
        FROM fact_orders fo
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        JOIN dim_city dc ON fo.city_id = dc.city_id
        WHERE fo.year = ?
        {cuisine_filter}
        GROUP BY dd.cuisine
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "dishes_by_restaurant": """
        SELECT
            dr.restaurant_name,
            dr.cuisine_type,
            dd.dish_name,
            dd.category,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating
        FROM fact_orders fo
        JOIN dim_restaurant dr ON fo.restaurant_id = dr.restaurant_id
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE fo.year = ? AND dr.restaurant_name LIKE ?
        GROUP BY dr.restaurant_name, dr.cuisine_type, dd.dish_name, dd.category
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "top_cities": """
        SELECT
            dc.city_name,
            dc.country,
            dc.region,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            ROUND(AVG(fo.avg_rating), 2) AS avg_rating,
            COUNT(DISTINCT dd.dish_name) AS dishes_sold
        FROM fact_orders fo
        JOIN dim_city dc ON fo.city_id = dc.city_id
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE fo.year = ?
        {cuisine_filter}
        GROUP BY dc.city_name, dc.country, dc.region
        ORDER BY total_orders DESC
        LIMIT ?
    """,
    "cuisine_order_trends": """
        SELECT
            fo.year,
            fo.month,
            dd.cuisine,
            SUM(fo.orders_count) AS total_orders,
            ROUND(SUM(fo.revenue_eur), 2) AS total_revenue_eur,
            COUNT(DISTINCT dd.dish_name) AS dish_count
        FROM fact_orders fo
        JOIN dim_dish dd ON fo.dish_id = dd.dish_id
        WHERE fo.year = ? AND dd.cuisine LIKE ?
        GROUP BY fo.year, fo.month, dd.cuisine
        ORDER BY fo.year, fo.month
        LIMIT ?
    """,
}


def build_query_params(query_type: str, params: QueryParameters) -> List[Any]:
    """Build the positional parameter list (excluding filter-injected params)
    for a given query type. The full list is assembled by `build_final_params`
    which also appends any optional-filter parameters."""

    year = params.year or 2024
    limit = params.limit or 20

    param_builders = {
        "orders_by_dish": lambda: [
            f"%{params.dish_name}%" if params.dish_name else "%",
            year,
            limit,
        ],
        "orders_by_country": lambda: [params.country or "Germany", year, limit],
        "orders_by_region": lambda: [f"%{params.region or 'Europe'}%", year, limit],
        "order_trends": lambda: [year, limit],
        "top_dishes": lambda: [year, limit],
        "cuisine_analysis": lambda: [year, limit],
        "dishes_by_restaurant": lambda: [
            year,
            f"%{params.restaurant}%" if params.restaurant else "%",
            limit,
        ],
        "top_cities": lambda: [year, limit],
        "cuisine_order_trends": lambda: [
            year,
            f"%{params.cuisine}%" if params.cuisine else "%",
            limit,
        ],
    }

    return param_builders.get(query_type, lambda: [])()


# Which query types accept the optional `cuisine` filter. Kept as a set so
# `build_query_with_filters` and `build_final_params` stay in sync.
_CUISINE_FILTERABLE = {
    "orders_by_country",
    "orders_by_region",
    "order_trends",
    "top_dishes",
    "cuisine_analysis",
    "top_cities",
}


def build_query_with_filters(query_type: str, params: QueryParameters) -> str:
    """Format the query template with any optional filter clauses inserted."""
    base_query = QUERY_TEMPLATES.get(query_type, "")

    city_filter = ""
    cuisine_filter = ""

    # `orders_by_dish` is the one query that narrows by city (not cuisine).
    if query_type == "orders_by_dish" and params.city:
        city_filter = "AND dc.city_name = ?"

    if query_type in _CUISINE_FILTERABLE and params.cuisine:
        cuisine_filter = "AND dd.cuisine = ?"

    return base_query.format(city_filter=city_filter, cuisine_filter=cuisine_filter)


def build_final_params(query_type: str, params: QueryParameters) -> List[Any]:
    """Build the final parameter list, inserting optional filter values in
    the exact position the sqlite3 `?` placeholders expect them."""
    base_params = build_query_params(query_type, params)

    # Inserted before the trailing LIMIT so it aligns with the `?` that
    # build_query_with_filters adds via the `{city_filter}` slot.
    if query_type == "orders_by_dish" and params.city:
        base_params.insert(-1, params.city)

    elif query_type in _CUISINE_FILTERABLE and params.cuisine:
        base_params.insert(-1, params.cuisine)

    return base_params


# Available query types for documentation and validation.
AVAILABLE_QUERY_TYPES = list(QUERY_TEMPLATES.keys())
