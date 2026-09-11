"""Tests for Belief, Memory, and validation"""
import pytest
from pydantic import ValidationError
from src.domain import Belief, Memory, EmotionalState


class TestBelief:
    """Tests for Belief domain model"""

    def test_belief_creation(self):
        """Test valid belief creation"""
        belief = Belief(
            id="bel_001",
            statement="It is raining",
            confidence=0.8,
            source="observation",
            character_id="char_001",
        )
        assert belief.id == "bel_001"
        assert belief.confidence == 0.8

    def test_belief_confidence_valid_range(self):
        """Test that confidence can range from 0.0 to 1.0"""
        # Min
        belief_min = Belief(
            id="bel_min",
            statement="Test",
            confidence=0.0,
            character_id="char_001",
        )
        assert belief_min.confidence == 0.0

        # Max
        belief_max = Belief(
            id="bel_max",
            statement="Test",
            confidence=1.0,
            character_id="char_001",
        )
        assert belief_max.confidence == 1.0

        # Mid
        belief_mid = Belief(
            id="bel_mid",
            statement="Test",
            confidence=0.5,
            character_id="char_001",
        )
        assert belief_mid.confidence == 0.5

    def test_belief_invalid_confidence_too_high(self):
        """Test that confidence > 1.0 raises error"""
        with pytest.raises(ValidationError):
            Belief(
                id="bel_invalid",
                statement="Test",
                confidence=1.1,
                character_id="char_001",
            )

    def test_belief_invalid_confidence_too_low(self):
        """Test that confidence < 0.0 raises error"""
        with pytest.raises(ValidationError):
            Belief(
                id="bel_invalid",
                statement="Test",
                confidence=-0.1,
                character_id="char_001",
            )

    def test_belief_with_optional_source(self):
        """Test belief without source"""
        belief = Belief(
            id="bel_001",
            statement="Test",
            confidence=0.5,
            character_id="char_001",
        )
        assert belief.source is None


class TestMemory:
    """Tests for Memory domain model"""

    def test_memory_creation(self):
        """Test valid memory creation"""
        memory = Memory(
            id="mem_001",
            character_id="char_001",
            event_id="evt_001",
            summary="I saw something",
            importance=0.7,
            emotional_weight=0.5,
            tick=10,
        )
        assert memory.id == "mem_001"
        assert memory.importance == 0.7
        assert memory.emotional_weight == 0.5

    def test_memory_importance_valid_range(self):
        """Test that importance can range from 0.0 to 1.0"""
        # Min
        memory_min = Memory(
            id="mem_min",
            character_id="char_001",
            summary="Test",
            importance=0.0,
            emotional_weight=0.0,
            tick=0,
        )
        assert memory_min.importance == 0.0

        # Max
        memory_max = Memory(
            id="mem_max",
            character_id="char_001",
            summary="Test",
            importance=1.0,
            emotional_weight=0.0,
            tick=0,
        )
        assert memory_max.importance == 1.0

    def test_memory_invalid_importance_too_high(self):
        """Test that importance > 1.0 raises error"""
        with pytest.raises(ValidationError):
            Memory(
                id="mem_invalid",
                character_id="char_001",
                summary="Test",
                importance=1.1,
                emotional_weight=0.0,
                tick=0,
            )

    def test_memory_invalid_importance_too_low(self):
        """Test that importance < 0.0 raises error"""
        with pytest.raises(ValidationError):
            Memory(
                id="mem_invalid",
                character_id="char_001",
                summary="Test",
                importance=-0.1,
                emotional_weight=0.0,
                tick=0,
            )

    def test_memory_emotional_weight_valid_range(self):
        """Test that emotional_weight can range from -1.0 to 1.0"""
        # Min
        memory_min = Memory(
            id="mem_neg",
            character_id="char_001",
            summary="Test",
            importance=0.5,
            emotional_weight=-1.0,
            tick=0,
        )
        assert memory_min.emotional_weight == -1.0

        # Max
        memory_max = Memory(
            id="mem_pos",
            character_id="char_001",
            summary="Test",
            importance=0.5,
            emotional_weight=1.0,
            tick=0,
        )
        assert memory_max.emotional_weight == 1.0

        # Neutral
        memory_neutral = Memory(
            id="mem_neutral",
            character_id="char_001",
            summary="Test",
            importance=0.5,
            emotional_weight=0.0,
            tick=0,
        )
        assert memory_neutral.emotional_weight == 0.0

    def test_memory_invalid_emotional_weight_too_high(self):
        """Test that emotional_weight > 1.0 raises error"""
        with pytest.raises(ValidationError):
            Memory(
                id="mem_invalid",
                character_id="char_001",
                summary="Test",
                importance=0.5,
                emotional_weight=1.1,
                tick=0,
            )

    def test_memory_invalid_emotional_weight_too_low(self):
        """Test that emotional_weight < -1.0 raises error"""
        with pytest.raises(ValidationError):
            Memory(
                id="mem_invalid",
                character_id="char_001",
                summary="Test",
                importance=0.5,
                emotional_weight=-1.1,
                tick=0,
            )

    def test_memory_with_participants(self):
        """Test memory with multiple participants"""
        memory = Memory(
            id="mem_001",
            character_id="char_001",
            summary="Meeting with others",
            importance=0.8,
            emotional_weight=0.3,
            participants=["char_002", "char_003"],
            tick=5,
        )
        assert len(memory.participants) == 2
        assert "char_002" in memory.participants


class TestEmotionalState:
    """Tests for EmotionalState domain model"""

    def test_emotional_state_creation(self):
        """Test valid emotional state creation"""
        emotion = EmotionalState(
            happiness=0.5,
            fear=0.3,
            anger=0.1,
            trust=0.7,
            curiosity=0.8,
        )
        assert emotion.happiness == 0.5
        assert emotion.fear == 0.3

    def test_emotional_state_all_emotions_in_range(self):
        """Test that all emotions are validated"""
        # Valid extremes
        emotion_all_min = EmotionalState(
            happiness=-1.0,
            fear=-1.0,
            anger=-1.0,
            trust=-1.0,
            curiosity=-1.0,
        )
        assert emotion_all_min.happiness == -1.0

        emotion_all_max = EmotionalState(
            happiness=1.0,
            fear=1.0,
            anger=1.0,
            trust=1.0,
            curiosity=1.0,
        )
        assert emotion_all_max.happiness == 1.0

    def test_emotional_state_invalid_happiness(self):
        """Test that invalid happiness raises error"""
        with pytest.raises(ValidationError):
            EmotionalState(
                happiness=1.5,
                fear=0.0,
                anger=0.0,
                trust=0.0,
                curiosity=0.0,
            )

    def test_emotional_state_default_values(self):
        """Test default emotional state values"""
        emotion = EmotionalState()
        assert emotion.happiness == 0.0
        assert emotion.fear == 0.0
        assert emotion.anger == 0.0
        assert emotion.trust == 0.0
        assert emotion.curiosity == 0.0
