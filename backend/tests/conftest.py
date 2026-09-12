"""Pytest configuration ensuring deterministic offline test execution."""
import pytest

@pytest.fixture(autouse=True)
def ensure_offline_testing(monkeypatch):
    """Ensure automated unit tests run 100% offline without hitting live cloud APIs."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
