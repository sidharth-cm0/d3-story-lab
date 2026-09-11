"""Tests for Milestone 6: AI Provider Abstraction"""
import pytest
from pydantic import BaseModel, Field
from src.providers import LLMProvider, MockLLMProvider, GeminiProvider


class SamplePlan(BaseModel):
    title: str = Field(...)
    steps: int = Field(default=3)
    approved: bool = Field(default=True)


class TestProviders:
    """Tests for LLM Provider abstraction and mock execution"""

    def test_mock_provider_text_generation(self):
        """Test MockLLMProvider text generation and substring matching"""
        provider = MockLLMProvider()
        provider.register_text_response("hotel intrigue", "A story of corporate espionage.")

        res = provider.generate_text("Tell me about Hotel Intrigue.")
        assert "corporate espionage" in res

        fallback = provider.generate_text("Something completely unrelated.")
        assert "Deterministic mock text response." in fallback
        assert len(provider.call_history) == 2

    def test_mock_provider_structured_generation(self):
        """Test MockLLMProvider generates valid Pydantic schema instances"""
        provider = MockLLMProvider()
        result = provider.generate_structured(SamplePlan, "Generate a sample plan")

        assert isinstance(result, SamplePlan)
        assert result.title.startswith("mock_")
        assert result.steps == 3
        assert result.approved is True

    def test_mock_provider_custom_structured_handler(self):
        """Test registering a custom structured generator"""
        provider = MockLLMProvider()
        provider.register_structured_handler(
            SamplePlan,
            lambda prompt: SamplePlan(title="Custom Title", steps=10, approved=False),
        )

        result = provider.generate_structured(SamplePlan, "Prompt")
        assert result.title == "Custom Title"
        assert result.steps == 10
        assert result.approved is False

    def test_gemini_provider_unconfigured_error(self):
        """Test GeminiProvider without API key raises informative ValueError"""
        provider = GeminiProvider(api_key="")
        with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
            provider.generate_text("Test")
