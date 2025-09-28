"""Tests for SQL tools."""

import pytest
from unittest.mock import patch, MagicMock

from assistant.sql_tools import (
    get_sales_by_model,
    get_sales_by_country,
    get_sales_by_region,
    get_sales_trends,
    get_top_performing_models,
    get_powertrain_analysis,
    compare_models_by_brand,
    get_top_countries_by_sales,
    get_powertrain_sales_trends,
    get_database_schema,
    INDIVIDUAL_SQL_TOOLS,
    get_sql_tools_info,
)
from assistant.sql_schemas import QueryParameters


class TestSQLTools:
    """Test individual SQL tools."""

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_sales_by_model(self, mock_executor):
        """Test get_sales_by_model tool."""
        mock_executor.execute_query.return_value = "Mock sales data"
        
        result = get_sales_by_model.invoke({
            "model_name": "RAV4",
            "year": 2024,
            "country": "Germany",
            "limit": 10
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "sales_by_model"  # query_name
        assert isinstance(call_args[0][1], QueryParameters)  # params
        assert call_args[0][1].model_name == "RAV4"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].country == "Germany"
        assert call_args[0][1].limit == 10
        assert result == "Mock sales data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_sales_by_country(self, mock_executor):
        """Test get_sales_by_country tool."""
        mock_executor.execute_query.return_value = "Mock country data"
        
        result = get_sales_by_country.invoke({
            "country": "Germany",
            "year": 2023,
            "brand": "Toyota",
            "limit": 15
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "sales_by_country"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].country == "Germany"
        assert call_args[0][1].year == 2023
        assert call_args[0][1].brand == "Toyota"
        assert call_args[0][1].limit == 15
        assert result == "Mock country data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_sales_by_region(self, mock_executor):
        """Test get_sales_by_region tool."""
        mock_executor.execute_query.return_value = "Mock region data"
        
        result = get_sales_by_region.invoke({
            "region": "Europe",
            "year": 2024,
            "brand": "Lexus",
            "limit": 20
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "sales_by_region"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].region == "Europe"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Lexus"
        assert call_args[0][1].limit == 20
        assert result == "Mock region data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_sales_trends(self, mock_executor):
        """Test get_sales_trends tool."""
        mock_executor.execute_query.return_value = "Mock trends data"
        
        result = get_sales_trends.invoke({
            "year": 2024,
            "brand": "Toyota",
            "limit": 25
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "sales_trends"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Toyota"
        assert call_args[0][1].limit == 25
        assert result == "Mock trends data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_top_performing_models(self, mock_executor):
        """Test get_top_performing_models tool."""
        mock_executor.execute_query.return_value = "Mock top models data"
        
        result = get_top_performing_models.invoke({
            "year": 2024,
            "brand": "Lexus",
            "limit": 5
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "top_performers"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Lexus"
        assert call_args[0][1].limit == 5
        assert result == "Mock top models data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_powertrain_analysis(self, mock_executor):
        """Test get_powertrain_analysis tool."""
        mock_executor.execute_query.return_value = "Mock powertrain data"
        
        result = get_powertrain_analysis.invoke({
            "year": 2024,
            "brand": "Toyota",
            "limit": 30
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "powertrain_analysis"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Toyota"
        assert call_args[0][1].limit == 30
        assert result == "Mock powertrain data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_compare_models_by_brand(self, mock_executor):
        """Test compare_models_by_brand tool."""
        mock_executor.execute_query.return_value = "Mock comparison data"
        
        result = compare_models_by_brand.invoke({
            "brand": "Toyota",
            "year": 2024,
            "limit": 10
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "model_comparison"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].brand == "Toyota"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].limit == 10
        assert result == "Mock comparison data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_top_countries_by_sales(self, mock_executor):
        """Test get_top_countries_by_sales tool."""
        mock_executor.execute_query.return_value = "Mock top countries data"
        
        result = get_top_countries_by_sales.invoke({
            "year": 2024,
            "brand": "Lexus",
            "limit": 8
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "top_countries"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Lexus"
        assert call_args[0][1].limit == 8
        assert result == "Mock top countries data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_powertrain_sales_trends(self, mock_executor):
        """Test get_powertrain_sales_trends tool."""
        mock_executor.execute_query.return_value = "Mock powertrain trends data"
        
        result = get_powertrain_sales_trends.invoke({
            "powertrain": "Hybrid",
            "year": 2024,
            "brand": "Toyota",
            "limit": 12
        })
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "powertrain_trends"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].powertrain == "Hybrid"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].brand == "Toyota"
        assert call_args[0][1].limit == 12
        assert result == "Mock powertrain trends data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_database_schema(self, mock_executor):
        """Test get_database_schema tool."""
        mock_executor.execute_query.return_value = "Mock schema data"
        
        result = get_database_schema.invoke({})
        
        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args
        
        assert call_args[0][0] == "schema_info"
        assert isinstance(call_args[0][1], QueryParameters)
        assert result == "Mock schema data"

    def test_default_parameters(self):
        """Test that default parameters work correctly."""
        with patch("assistant.sql_tools.simple_sql_executor") as mock_executor:
            mock_executor.execute_query.return_value = "Mock data"
            
            # Test with minimal parameters
            get_sales_by_model.invoke({"model_name": "RAV4"})
            
            call_args = mock_executor.execute_query.call_args
            params = call_args[0][1]
            
            assert params.model_name == "RAV4"
            assert params.year == 2024  # default
            assert params.country is None  # default
            assert params.limit == 20  # default

    def test_individual_sql_tools_list(self):
        """Test that INDIVIDUAL_SQL_TOOLS contains all expected tools."""
        expected_tools = [
            get_sales_by_model,
            get_sales_by_country,
            get_sales_by_region,
            get_sales_trends,
            get_top_performing_models,
            get_powertrain_analysis,
            compare_models_by_brand,
            get_top_countries_by_sales,
            get_powertrain_sales_trends,
            get_database_schema,
        ]
        
        assert len(INDIVIDUAL_SQL_TOOLS) == len(expected_tools)
        
        for tool in expected_tools:
            assert tool in INDIVIDUAL_SQL_TOOLS

    def test_get_sql_tools_info(self):
        """Test get_sql_tools_info function."""
        info = get_sql_tools_info()
        
        assert "total_tools" in info
        assert "tool_names" in info
        assert "description" in info
        assert "security_features" in info
        
        assert info["total_tools"] == len(INDIVIDUAL_SQL_TOOLS)
        assert len(info["tool_names"]) == len(INDIVIDUAL_SQL_TOOLS)
        assert isinstance(info["security_features"], list)
        assert len(info["security_features"]) > 0
