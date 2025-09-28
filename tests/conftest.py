"""Pytest configuration and fixtures."""

import pytest
import os
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_openai_api_key():
    """Mock OpenAI API key for all tests."""
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key-for-testing"}):
        yield
