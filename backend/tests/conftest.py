"""Pytest configuration ensuring deterministic offline test execution."""
import pytest

@pytest.fixture(autouse=True)
def ensure_offline_testing(monkeypatch):
    """Ensure automated unit tests run 100% offline without hitting live cloud APIs."""
    monkeypatch.setenv("USE_MOCK_LLM", "1")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("ON_DEMAND_API_KEY", raising=False)
    monkeypatch.delenv("HUGGINGFACE_API_KEY", raising=False)
    monkeypatch.delenv("STORYBOARD_RENDER_PROVIDER", raising=False)
    monkeypatch.delenv("STORYBOARD_PROVIDER", raising=False)
    monkeypatch.delenv("STORYBOARD_RUNTIME_URL", raising=False)
    monkeypatch.delenv("STORYBOARD_MODEL", raising=False)
