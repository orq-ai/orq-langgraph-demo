"""Tests for SQL tools."""

from unittest.mock import patch

from assistant.sql_schemas import QueryParameters
from assistant.sql_tools import (
    SQL_TOOLS,
    compare_dishes_by_restaurant,
    get_cuisine_analysis,
    get_cuisine_order_trends,
    get_order_trends,
    get_orders_by_country,
    get_orders_by_dish,
    get_orders_by_region,
    get_top_cities_by_orders,
    get_top_dishes,
)


class TestSQLTools:
    """Test individual SQL tools."""

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_orders_by_dish(self, mock_executor):
        """Test get_orders_by_dish tool."""
        mock_executor.execute_query.return_value = "Mock orders data"

        result = get_orders_by_dish.invoke(
            {"dish_name": "Margherita Pizza", "year": 2024, "city": "Berlin", "limit": 10}
        )

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "orders_by_dish"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].dish_name == "Margherita Pizza"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].city == "Berlin"
        assert call_args[0][1].limit == 10
        assert result == "Mock orders data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_orders_by_country(self, mock_executor):
        """Test get_orders_by_country tool."""
        mock_executor.execute_query.return_value = "Mock country data"

        result = get_orders_by_country.invoke(
            {"country": "Germany", "year": 2024, "cuisine": "Italian", "limit": 15}
        )

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "orders_by_country"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].country == "Germany"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Italian"
        assert call_args[0][1].limit == 15
        assert result == "Mock country data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_orders_by_region(self, mock_executor):
        """Test get_orders_by_region tool."""
        mock_executor.execute_query.return_value = "Mock region data"

        result = get_orders_by_region.invoke(
            {"region": "Europe", "year": 2024, "cuisine": "Japanese", "limit": 20}
        )

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "orders_by_region"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].region == "Europe"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Japanese"
        assert call_args[0][1].limit == 20
        assert result == "Mock region data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_order_trends(self, mock_executor):
        """Test get_order_trends tool."""
        mock_executor.execute_query.return_value = "Mock trends data"

        result = get_order_trends.invoke({"year": 2024, "cuisine": "Italian", "limit": 25})

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "order_trends"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Italian"
        assert call_args[0][1].limit == 25
        assert result == "Mock trends data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_top_dishes(self, mock_executor):
        """Test get_top_dishes tool."""
        mock_executor.execute_query.return_value = "Mock top dishes data"

        result = get_top_dishes.invoke({"year": 2024, "cuisine": "Japanese", "limit": 5})

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "top_dishes"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Japanese"
        assert call_args[0][1].limit == 5
        assert result == "Mock top dishes data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_cuisine_analysis(self, mock_executor):
        """Test get_cuisine_analysis tool."""
        mock_executor.execute_query.return_value = "Mock cuisine data"

        result = get_cuisine_analysis.invoke({"year": 2024, "cuisine": "Italian", "limit": 30})

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "cuisine_analysis"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Italian"
        assert call_args[0][1].limit == 30
        assert result == "Mock cuisine data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_compare_dishes_by_restaurant(self, mock_executor):
        """Test compare_dishes_by_restaurant tool."""
        mock_executor.execute_query.return_value = "Mock comparison data"

        result = compare_dishes_by_restaurant.invoke(
            {"restaurant": "Trattoria Marco", "year": 2024, "limit": 10}
        )

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "dishes_by_restaurant"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].restaurant == "Trattoria Marco"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].limit == 10
        assert result == "Mock comparison data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_top_cities_by_orders(self, mock_executor):
        """Test get_top_cities_by_orders tool."""
        mock_executor.execute_query.return_value = "Mock top cities data"

        result = get_top_cities_by_orders.invoke({"year": 2024, "cuisine": "Italian", "limit": 8})

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "top_cities"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].year == 2024
        assert call_args[0][1].cuisine == "Italian"
        assert call_args[0][1].limit == 8
        assert result == "Mock top cities data"

    @patch("assistant.sql_tools.simple_sql_executor")
    def test_get_cuisine_order_trends(self, mock_executor):
        """Test get_cuisine_order_trends tool."""
        mock_executor.execute_query.return_value = "Mock cuisine trends data"

        result = get_cuisine_order_trends.invoke({"cuisine": "Japanese", "year": 2024, "limit": 12})

        mock_executor.execute_query.assert_called_once()
        call_args = mock_executor.execute_query.call_args

        assert call_args[0][0] == "cuisine_order_trends"
        assert isinstance(call_args[0][1], QueryParameters)
        assert call_args[0][1].cuisine == "Japanese"
        assert call_args[0][1].year == 2024
        assert call_args[0][1].limit == 12
        assert result == "Mock cuisine trends data"

    def test_default_parameters(self):
        """Test that default parameters work correctly."""
        with patch("assistant.sql_tools.simple_sql_executor") as mock_executor:
            mock_executor.execute_query.return_value = "Mock data"

            # Test with minimal parameters
            get_orders_by_dish.invoke({"dish_name": "Margherita Pizza"})

            call_args = mock_executor.execute_query.call_args
            params = call_args[0][1]

            assert params.dish_name == "Margherita Pizza"
            assert params.year == 2024  # default
            assert params.city is None  # default
            assert params.limit == 20  # default

    def test_individual_sql_tools_list(self):
        """Test that SQL_TOOLS contains all expected tools."""
        expected_tools = [
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

        assert len(SQL_TOOLS) == len(expected_tools)

        for tool in expected_tools:
            assert tool in SQL_TOOLS
