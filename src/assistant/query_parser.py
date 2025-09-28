"""LLM-based query intent parser for secure SQL generation.

This module uses LLM to parse natural language queries into structured parameters
for secure SQL execution.
"""

import logging
import re
from typing import Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from core.settings import settings

from .secure_sql import QueryParameters, QueryType
from .utils import load_chat_model

logger = logging.getLogger(__name__)


class SQLQueryIntent(BaseModel):
    """Structured output for SQL query intent classification."""

    query_type: str = Field(
        description="The type of SQL query needed: sales_by_model, sales_by_country, sales_by_region, sales_trend, model_comparison, powertrain_analysis, top_performers, or schema_info"
    )
    model_name: Optional[str] = Field(
        description="Vehicle model name if specified (e.g., 'RAV4', 'Prius', 'Camry')"
    )
    country: Optional[str] = Field(
        description="Country name if specified (e.g., 'Germany', 'France', 'Italy')"
    )
    region: Optional[str] = Field(
        description="Region name if specified (e.g., 'Europe', 'Asia', 'Americas')"
    )
    brand: Optional[str] = Field(description="Brand name if specified ('Toyota' or 'Lexus')")
    powertrain: Optional[str] = Field(
        description="Powertrain type if specified (e.g., 'HEV', 'BEV', 'ICE')"
    )
    year: Optional[int] = Field(description="Year if specified (e.g., 2024, 2023)")
    month: Optional[int] = Field(description="Month if specified (1-12)")
    time_period: Optional[str] = Field(
        description="Time period description (e.g., 'monthly', 'quarterly', 'yearly')"
    )
    comparison_type: Optional[str] = Field(
        description="Type of comparison if requested (e.g., 'by_country', 'by_model', 'by_powertrain')"
    )
    limit: Optional[int] = Field(
        description="Number of results requested (e.g., 'top 10', 'top 5')"
    )


class LLMQueryIntentParser:
    """Parse natural language queries into structured SQL parameters using LLM."""

    def __init__(self):
        # Use the existing load_chat_model utility that handles provider/model format
        self.llm = load_chat_model(settings.DEFAULT_MODEL)
        # Set temperature to 0 for deterministic intent classification
        self.llm.temperature = 0
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        """Create system prompt for intent classification."""
        return """You are a SQL query intent classifier for Toyota/Lexus sales data analysis.

Your task is to analyze natural language questions and extract structured information for secure SQL query generation.

Available Query Types:
- sales_by_model: Sales data for specific vehicle models
- sales_by_country: Sales data for specific countries
- sales_by_region: Sales data for geographic regions
- sales_trend: Time-based sales trends and patterns
- model_comparison: Comparing different models
- powertrain_analysis: Analysis by powertrain type (HEV, BEV, ICE)
- top_performers: Top performing models/countries/regions
- schema_info: Database structure information

Database Context:
- Vehicle Models: RAV4, Prius, Camry, Corolla, C-HR, Yaris Cross, UX, NX, RX, ES, etc.
- Countries: Germany, France, Italy, Spain, United Kingdom, Japan, USA, etc.
- Regions: Europe, Asia, Americas
- Brands: Toyota, Lexus
- Powertrains: HEV (Hybrid), BEV (Battery Electric), ICE (Internal Combustion)
- Time Range: 2020-2024 data available

Extract Parameters:
- Be specific with model names (use exact names like 'RAV4', not 'RAV4%')
- Use full country names ('Germany' not 'DE')
- Default to 2024 if no year specified
- Set reasonable limits (default 10-20 for top queries)
- For model matching, use the closest match from available models

Examples:
"RAV4 sales in Germany 2024" → query_type: sales_by_model, model_name: RAV4, country: Germany, year: 2024
"What were RAV4 sales in Germany in 2024?" → query_type: sales_by_model, model_name: RAV4, country: Germany, year: 2024
"Top 5 countries by Toyota sales" → query_type: top_performers, comparison_type: by_country, brand: Toyota, limit: 5
"Hybrid vehicle sales trends" → query_type: powertrain_analysis, powertrain: HEV, time_period: trends
"Compare Toyota and Lexus sales" → query_type: model_comparison, brand: Toyota, comparison_type: by_brand
"What tables are available?" → query_type: schema_info
"Show me European market performance" → query_type: sales_by_region, region: Europe
"Show me Toyota RAV4 sales by month in Germany for the year 2024" → query_type: sales_by_model, model_name: RAV4, country: Germany, year: 2024

IMPORTANT CLASSIFICATION RULES:
- If the question mentions a specific car model (RAV4, Prius, Camry, etc.), use sales_by_model
- If the question asks about sales data or performance, do NOT use schema_info
- Only use schema_info for questions about database structure, tables, or schema
- For sales questions, always classify based on the primary entity (model, country, region)

Always prioritize security and use exact parameter extraction. If uncertain about parameters, use safe defaults."""

    async def parse_query_intent(self, natural_query: str) -> Tuple[QueryType, QueryParameters]:
        """Parse natural language into structured query using LLM."""

        try:
            # Use LLM to classify intent and extract parameters
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"Parse this query: {natural_query}"),
            ]

            # Get structured output from LLM
            response = await self.llm.with_structured_output(SQLQueryIntent).ainvoke(messages)

            # Convert to our internal types
            query_type = self._map_query_type(response.query_type)
            params = self._build_parameters(response)

            # Validate and sanitize parameters
            params = self._validate_and_sanitize(params)

            logger.info(f"Parsed query intent: {query_type.value} for query: {natural_query[:100]}")
            return query_type, params

        except Exception as e:
            logger.error(f"Failed to parse query intent: {e}")
            # Fallback to safe default
            return QueryType.SCHEMA_INFO, QueryParameters()

    def _map_query_type(self, llm_query_type: str) -> QueryType:
        """Map LLM response to QueryType enum."""

        type_mapping = {
            "sales_by_model": QueryType.SALES_BY_MODEL,
            "sales_by_country": QueryType.SALES_BY_COUNTRY,
            "sales_by_region": QueryType.SALES_BY_REGION,
            "sales_trend": QueryType.SALES_TREND,
            "model_comparison": QueryType.MODEL_COMPARISON,
            "powertrain_analysis": QueryType.POWERTRAIN_ANALYSIS,
            "top_performers": QueryType.TOP_PERFORMERS,
            "schema_info": QueryType.SCHEMA_INFO,
        }

        return type_mapping.get(llm_query_type, QueryType.SCHEMA_INFO)

    def _build_parameters(self, response: SQLQueryIntent) -> QueryParameters:
        """Build QueryParameters from LLM response."""

        return QueryParameters(
            model_name=response.model_name,
            country=response.country,
            region=response.region,
            year=response.year or 2024,  # Default to current year
            month=response.month,
            brand=response.brand,
            powertrain=response.powertrain,
            limit=response.limit or 20,  # Reasonable default
            comparison_type=response.comparison_type,
            time_period=response.time_period,
        )

    def _validate_and_sanitize(self, params: QueryParameters) -> QueryParameters:
        """Validate and sanitize parameters for security."""

        # Validate year range
        if params.year and (params.year < 2020 or params.year > 2024):
            logger.warning(f"Invalid year {params.year}, defaulting to 2024")
            params.year = 2024

        # Validate month range
        if params.month and (params.month < 1 or params.month > 12):
            logger.warning(f"Invalid month {params.month}, setting to None")
            params.month = None

        # Validate limit
        if params.limit and (params.limit < 1 or params.limit > 100):
            logger.warning(f"Invalid limit {params.limit}, defaulting to 20")
            params.limit = 20

        # Sanitize string parameters (remove potential SQL injection chars)
        if params.model_name:
            params.model_name = re.sub(r"[^\w\s\-]", "", params.model_name)

        if params.country:
            params.country = re.sub(r"[^\w\s\-]", "", params.country)

        if params.region:
            params.region = re.sub(r"[^\w\s\-]", "", params.region)

        if params.brand:
            params.brand = re.sub(r"[^\w\s\-]", "", params.brand)

        if params.powertrain:
            params.powertrain = re.sub(r"[^\w\s\-]", "", params.powertrain)

        return params


class QueryIntentParser:
    """Synchronous wrapper for LLM-based intent parsing."""

    def __init__(self):
        self.async_parser = LLMQueryIntentParser()

    def parse_query_intent(self, natural_query: str) -> Tuple[QueryType, QueryParameters]:
        """Synchronous parsing method."""
        try:
            import asyncio
            import concurrent.futures

            # Create a wrapper function that runs the async code
            def run_async_in_thread():
                # Create a new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        self.async_parser.parse_query_intent(natural_query)
                    )
                finally:
                    new_loop.close()

            # Run the async function in a separate thread
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_async_in_thread)
                return future.result(timeout=30)

        except Exception as e:
            logger.error(f"Synchronous parsing failed: {e}")
            return QueryType.SCHEMA_INFO, QueryParameters()


# Global instance for use in tools
query_intent_parser = QueryIntentParser()
