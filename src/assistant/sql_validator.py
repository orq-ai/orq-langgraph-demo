"""Input validation and security scanning for SQL queries.

This module provides additional security validation for user inputs to detect
and prevent various attack patterns before they reach the LLM parser.
"""

import logging
import re
from typing import List, Tuple

logger = logging.getLogger(__name__)


class SQLSecurityValidator:
    """Security validator for SQL inputs with multiple detection layers."""

    def __init__(self):
        self.forbidden_patterns = self._init_forbidden_patterns()
        self.suspicious_patterns = self._init_suspicious_patterns()
        self.max_input_length = 2000
        self.max_special_char_ratio = 0.4

    def _init_forbidden_patterns(self) -> List[str]:
        """Initialize patterns that should never appear in user input."""
        return [
            # SQL injection patterns
            r"union\s+select",
            r";\s*drop\s+table",
            r";\s*delete\s+from",
            r";\s*insert\s+into",
            r";\s*update\s+set",
            r";\s*create\s+table",
            r";\s*alter\s+table",
            # Classic injection patterns
            r"'\s*or\s*'1'\s*=\s*'1",
            r"'\s*or\s*1\s*=\s*1",
            r"\'\s*or\s*\'\w*\'\s*=\s*\'\w*",
            r'"\s*or\s*"1"\s*=\s*"1',
            r"\bor\s+1\s*=\s*1\b",
            r"\bor\s+true\b",
            r"'\s*;\s*",
            # Comment injection
            r"--\s*[^\s]",  # SQL comments with content
            r"/\*.*\*/",  # Block comments
            # System functions (SQLite specific)
            r"sqlite_master",
            r"sqlite_sequence",
            r"pragma\s+",
            # String manipulation attacks
            r"char\s*\(",
            r"ascii\s*\(",
            r"substring\s*\(",
            r"concat\s*\(",
            # Conditional attacks
            r"case\s+when",
            r"if\s*\(",
            r"iif\s*\(",
            # Time-based attacks
            r"sleep\s*\(",
            r"waitfor\s+delay",
            r"benchmark\s*\(",
            # Union-based patterns
            r"null.*union",
            r"order\s+by\s+\d+",
            r"group\s+by\s+\d+",
        ]

    def _init_suspicious_patterns(self) -> List[str]:
        """Initialize patterns that warrant additional scrutiny."""
        return [
            # Multiple queries
            r";\s*select",
            r";\s*with",
            # Nested queries
            r"select.*select",
            r"\(\s*select",
            # Special characters clusters
            r"[\'\"]{2,}",
            r"[;]{2,}",
            r"[\(\)]{3,}",
            # Hex/encoded content
            r"0x[0-9a-f]+",
            r"%[0-9a-f]{2}",
            # Script injection attempts
            r"<script",
            r"javascript:",
            r"eval\s*\(",
        ]

    def validate_input(self, user_input: str) -> Tuple[bool, str, List[str]]:
        """
        Validate user input for security threats.

        Args:
            user_input: The user's input string to validate

        Returns:
            Tuple of (is_valid, reason, warnings)
        """
        warnings = []

        # Basic input sanitization
        if not user_input or not user_input.strip():
            return False, "Empty input provided", []

        user_input = user_input.strip()

        # Length check
        if len(user_input) > self.max_input_length:
            return False, f"Input too long ({len(user_input)} > {self.max_input_length} chars)", []

        # Convert to lowercase for pattern matching
        input_lower = user_input.lower()

        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE | re.DOTALL):
                logger.warning(f"Forbidden pattern detected: {pattern}")
                return False, f"Forbidden pattern detected: {pattern[:20]}...", []

        # Check for suspicious patterns (warnings, not blocks)
        for pattern in self.suspicious_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE | re.DOTALL):
                warnings.append(f"Suspicious pattern: {pattern[:20]}...")
                logger.info(f"Suspicious pattern detected: {pattern}")

        return True, "Input validation passed", warnings

    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input by removing/escaping dangerous characters.

        Args:
            user_input: The input to sanitize

        Returns:
            Sanitized input string
        """
        if not user_input:
            return ""

        # Remove null bytes
        sanitized = user_input.replace("\x00", "")

        # Remove control characters except newlines and tabs
        sanitized = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Limit consecutive special characters
        sanitized = re.sub(r"([^\w\s])\1{2,}", r"\1\1", sanitized)

        # Remove SQL comments
        sanitized = re.sub(r"--.*$", "", sanitized, flags=re.MULTILINE)
        sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized).strip()

        return sanitized

    def is_likely_natural_language(self, user_input: str) -> bool:
        """
        Determine if input looks like natural language rather than SQL.

        Args:
            user_input: The input to analyze

        Returns:
            True if input appears to be natural language
        """
        if not user_input:
            return False

        # Natural language indicators
        natural_indicators = [
            "what",
            "how",
            "show",
            "tell",
            "explain",
            "compare",
            "analyze",
            "sales",
            "toyota",
            "lexus",
            "model",
            "country",
            "year",
            "top",
            "best",
            "worst",
            "performance",
            "trend",
        ]

        # SQL indicators
        sql_indicators = [
            "select",
            "from",
            "where",
            "join",
            "union",
            "insert",
            "update",
            "delete",
            "drop",
            "create",
            "alter",
        ]

        input_lower = user_input.lower()
        words = input_lower.split()

        natural_count = sum(
            1 for word in words if any(indicator in word for indicator in natural_indicators)
        )
        sql_count = sum(
            1 for word in words if any(indicator in word for indicator in sql_indicators)
        )

        # More natural language indicators than SQL indicators
        return natural_count > sql_count

    def get_security_score(self, user_input: str) -> float:
        """
        Calculate a security score for the input (0.0 = dangerous, 1.0 = safe).

        Args:
            user_input: The input to score

        Returns:
            Security score between 0.0 and 1.0
        """
        if not user_input:
            return 0.0

        score = 1.0

        # Validate input
        is_valid, reason, warnings = self.validate_input(user_input)

        if not is_valid:
            return 0.0

        # Deduct points for warnings
        score -= len(warnings) * 0.1

        # Bonus for natural language
        if self.is_likely_natural_language(user_input):
            score += 0.1

        # Length penalty for very long inputs
        if len(user_input) > 500:
            score -= 0.1

        return max(0.0, min(1.0, score))


# Global validator instance
sql_security_validator = SQLSecurityValidator()
