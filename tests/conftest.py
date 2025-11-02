"""
Pytest configuration and fixtures for PipeWrench AI tests.
"""

import pytest
import sys
from pathlib import Path

# Add api directory to path
api_path = Path(__file__).parent.parent / "api"
sys.path.insert(0, str(api_path))


@pytest.fixture
def mock_anthropic_client(monkeypatch):
    """Mock Anthropic client for testing."""
    class MockMessage:
        def __init__(self, text):
            self.text = text
    
    class MockContent:
        def __init__(self, text):
            self.content = [MockMessage(text)]
    
    class MockAnthropicClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
        
        def messages_create(self, **kwargs):
            return MockContent("This is a mock response from Claude.")
    
    return MockAnthropicClient()


@pytest.fixture
def sample_session_id():
    """Return a sample session ID for testing."""
    return "test-session-12345"


@pytest.fixture
def sample_text_file_content():
    """Sample text file content for testing."""
    return b"This is a test document with some procedures and information."


@pytest.fixture
def sample_question():
    """Sample question for testing."""
    return "What are the safety procedures mentioned in the document?"
