"""Security tests for SQL injection protection in Toyota RAG Assistant.

This module tests the secure SQL implementation against various attack vectors
to ensure SQL injection vulnerabilities have been eliminated.
"""

from pathlib import Path
import sys

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from assistant.secure_sql import QueryParameters, QueryType, SecureSQLExecutor
from assistant.sql_tools import execute_sql_secure
from assistant.sql_validator import SQLSecurityValidator


class TestSQLInjectionProtection:
    """Test SQL injection protection mechanisms."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SQLSecurityValidator()
        self.executor = SecureSQLExecutor(":memory:")  # Use in-memory DB for testing

    def test_basic_sql_injection_patterns(self):
        """Test that basic SQL injection patterns are blocked."""

        malicious_inputs = [
            "'; DROP TABLE fact_sales; --",
            "' OR '1'='1",
            "1=1; INSERT INTO fact_sales VALUES (999, 'XX', 2025, 1, 0)",
            "UNION SELECT * FROM sqlite_master",
            "'; PRAGMA table_info(fact_sales); --",
            "1' AND (SELECT COUNT(*) FROM sqlite_master)>0 --",
            "RAV4'; DELETE FROM fact_sales WHERE 1=1; --",
        ]

        for malicious_input in malicious_inputs:
            is_valid, reason, warnings = self.validator.validate_input(malicious_input)
            assert not is_valid, f"Should block malicious input: {malicious_input}"
            assert "Forbidden pattern detected" in reason

    def test_union_based_attacks(self):
        """Test protection against UNION-based SQL injection."""

        union_attacks = [
            "RAV4 UNION SELECT sql FROM sqlite_master",
            "Germany' UNION SELECT name, sql, NULL FROM sqlite_master --",
            "2024 UNION ALL SELECT table_name FROM information_schema.tables",
            "1 UNION SELECT 1,2,3,4,5,version(),7,8,9",
        ]

        for attack in union_attacks:
            is_valid, reason, warnings = self.validator.validate_input(attack)
            assert not is_valid, f"Should block UNION attack: {attack}"

    def test_comment_injection_attacks(self):
        """Test protection against comment-based injection."""

        comment_attacks = [
            "RAV4 --",
            "Germany /* comment */ OR 1=1",
            "2024 -- this is a comment; DROP TABLE fact_sales;",
            "/* multi-line\ncomment */ SELECT * FROM sqlite_master",
        ]

        for attack in comment_attacks:
            is_valid, reason, warnings = self.validator.validate_input(attack)
            # Some may pass validation but should be sanitized
            if is_valid:
                sanitized = self.validator.sanitize_input(attack)
                assert "--" not in sanitized and "/*" not in sanitized

    def test_time_based_blind_injection(self):
        """Test protection against time-based attacks."""

        time_attacks = [
            "RAV4 AND (SELECT COUNT(*) FROM sqlite_master) > 0",
            "Germany; WAITFOR DELAY '00:00:05'",
            "2024 AND (CASE WHEN 1=1 THEN sleep(5) ELSE 1 END)",
            "SELECT * FROM fact_sales WHERE model_id = 1 AND (SELECT sleep(5))",
        ]

        for attack in time_attacks:
            is_valid, reason, warnings = self.validator.validate_input(attack)
            # Most should be blocked
            assert not is_valid or len(warnings) > 0

    def test_system_function_access(self):
        """Test that system functions are blocked."""

        system_attacks = [
            "SELECT * FROM sqlite_master",
            "PRAGMA table_info(fact_sales)",
            "SELECT sqlite_version()",
            ".tables",
            ".schema fact_sales",
        ]

        for attack in system_attacks:
            is_valid, reason, warnings = self.validator.validate_input(attack)
            assert not is_valid, f"Should block system function: {attack}"

    def test_legitimate_queries_pass(self):
        """Test that legitimate natural language queries pass validation."""

        legitimate_queries = [
            "What were RAV4 sales in Germany in 2024?",
            "Show me Toyota sales by powertrain",
            "Compare Lexus sales across European countries",
            "Top 10 performing models this year",
            "Monthly sales trends for hybrid vehicles",
            "Sales data for Prius in France",
            "European market performance analysis",
        ]

        for query in legitimate_queries:
            is_valid, reason, warnings = self.validator.validate_input(query)
            assert is_valid, f"Legitimate query should pass: {query}"

            # Check security score
            score = self.validator.get_security_score(query)
            assert score >= 0.5, f"Legitimate query should have good security score: {score}"

    def test_parameter_validation(self):
        """Test parameter validation in QueryParameters."""

        # Invalid year
        params = QueryParameters(year=2050)
        assert not params.validate()

        # Invalid month
        params = QueryParameters(month=13)
        assert not params.validate()

        # Invalid limit
        params = QueryParameters(limit=-5)
        assert not params.validate()

        # Valid parameters
        params = QueryParameters(year=2024, month=6, limit=10)
        assert params.validate()

    def test_input_sanitization(self):
        """Test input sanitization removes dangerous content."""

        test_cases = [
            ("Normal query", "Normal query"),
            ("Query with -- comment", "Query with"),
            ("Query /* block comment */ here", "Query  here"),
            ("Multiple    spaces", "Multiple spaces"),
            ("Query\x00with\x01null\x1fbytes", "Querywithbytes"),
        ]

        for input_text, expected_pattern in test_cases:
            sanitized = self.validator.sanitize_input(input_text)
            assert expected_pattern in sanitized or sanitized == expected_pattern

    def test_natural_language_detection(self):
        """Test natural language vs SQL detection."""

        natural_queries = [
            "What are the sales for RAV4?",
            "Show me Toyota performance",
            "Compare hybrid vehicle sales",
        ]

        sql_queries = [
            "SELECT * FROM fact_sales",
            "INSERT INTO table VALUES",
            "UPDATE fact_sales SET contracts = 0",
        ]

        for query in natural_queries:
            assert self.validator.is_likely_natural_language(query)

        for query in sql_queries:
            assert not self.validator.is_likely_natural_language(query)

    def test_security_score_calculation(self):
        """Test security score calculation."""

        # High security score queries
        safe_queries = ["RAV4 sales in Germany", "Toyota performance 2024", "Show me sales data"]

        # Low security score queries
        risky_queries = [
            "'; DROP TABLE users; --",
            "UNION SELECT * FROM sqlite_master",
            "1=1 OR 1=1 AND 2=2",
        ]

        for query in safe_queries:
            score = self.validator.get_security_score(query)
            assert score >= 0.7, f"Safe query should have high score: {query}"

        for query in risky_queries:
            score = self.validator.get_security_score(query)
            assert score <= 0.2, f"Risky query should have low score: {query}"


class TestSecureQueryExecution:
    """Test secure query execution end-to-end."""

    def test_parameterized_query_execution(self):
        """Test that parameterized queries execute safely."""

        # Test with in-memory database
        executor = SecureSQLExecutor(":memory:")

        # These should execute without SQL injection
        safe_params = QueryParameters(model_name="RAV4", year=2024, limit=10)

        # Execute should not raise exceptions
        result = executor.execute_secure_query(QueryType.SCHEMA_INFO, safe_params)
        assert "error" not in result.lower() or "no results" in result.lower()

    def test_secure_tool_integration(self):
        """Test the complete secure tool pipeline."""

        # Test legitimate queries
        legitimate_queries = [
            "Show me database schema",
            "What tables are available?",
            "Database structure information",
        ]

        for query in legitimate_queries:
            # Should not raise exceptions
            try:
                result = execute_sql_secure(query)
                assert isinstance(result, str)
                assert "SQL execution error" not in result or "validation" in result
            except Exception as e:
                pytest.fail(f"Secure tool should handle query safely: {e}")

    def test_malicious_input_blocked_end_to_end(self):
        """Test that malicious inputs are blocked in the complete pipeline."""

        malicious_queries = [
            "'; DROP TABLE fact_sales; --",
            "UNION SELECT * FROM sqlite_master",
            "1=1 OR 1=1",
        ]

        for query in malicious_queries:
            result = execute_sql_secure(query)
            assert "validation" in result.lower() or "error" in result.lower()
            assert "drop" not in result.lower()
            assert "sqlite_master" not in result.lower()


if __name__ == "__main__":
    # Run basic tests
    test_injection = TestSQLInjectionProtection()
    test_injection.setup_method()

    print("Testing SQL injection protection...")

    # Test basic injection patterns
    test_injection.test_basic_sql_injection_patterns()
    print("Basic SQL injection patterns blocked")

    # Test legitimate queries
    test_injection.test_legitimate_queries_pass()
    print("Legitimate queries pass validation")

    # Test parameter validation
    test_injection.test_parameter_validation()
    print("Parameter validation working")

    # Test input sanitization
    test_injection.test_input_sanitization()
    print("Input sanitization working")

    print("\nSQL injection protection tests passed!")
    print(
        "The secure SQL implementation successfully blocks malicious inputs while allowing legitimate queries."
    )
