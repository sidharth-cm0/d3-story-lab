"""Tests for Milestone 5: Belief and Relationship Evolution"""
import pytest
from src.demo_world import create_demo_world
from src.evolution import BeliefUpdater, RelationshipUpdater, EmotionUpdater


class TestBeliefEvolution:
    """Tests for forming, reinforcing, and weakening beliefs with bounded confidence"""

    def test_belief_formation_and_reinforcement(self):
        """Test forming a new belief and reinforcing it with confidence bounded at 1.0"""
        world = create_demo_world()
        bel = BeliefUpdater.form_or_reinforce_belief(
            world,
            character_id="char_arjun",
            statement="Maya has a second phone hidden in the suitcase",
            initial_confidence=0.7,
        )
        assert bel.confidence == 0.7
        assert bel.id in world.characters["char_arjun"].beliefs

        # Reinforce twice
        bel_reinforced = BeliefUpdater.form_or_reinforce_belief(
            world,
            character_id="char_arjun",
            statement="Maya has a second phone hidden in the suitcase",
            confidence_delta=0.2,
        )
        assert bel_reinforced.id == bel.id
        assert bel_reinforced.confidence == 0.9

        # Reinforce past 1.0 -> must be clamped to 1.0
        bel_clamped = BeliefUpdater.form_or_reinforce_belief(
            world,
            character_id="char_arjun",
            statement="Maya has a second phone hidden in the suitcase",
            confidence_delta=0.5,
        )
        assert bel_clamped.confidence == 1.0

    def test_weaken_belief_on_contradiction(self):
        """Test weakening belief confidence down towards 0.0"""
        world = create_demo_world()
        bel = world.beliefs["bel_arjun_001"]
        initial_conf = bel.confidence

        weakened = BeliefUpdater.weaken_belief(world, bel.id, penalty=0.4)
        assert weakened.confidence == round(initial_conf - 0.4, 2)

        # Weaken heavily past 0.0 -> clamped to 0.0
        weakened_clamped = BeliefUpdater.weaken_belief(world, bel.id, penalty=1.0)
        assert weakened_clamped.confidence == 0.0


class TestRelationshipAndEmotionEvolution:
    """Tests for trust, affinity, and emotional adjustments"""

    def test_deception_reduces_trust(self):
        """Test discovering a contradiction or deception significantly degrades trust"""
        world = create_demo_world()
        rel_initial = world.relationships["rel_001"]
        initial_trust = rel_initial.trust

        updated_rel = RelationshipUpdater.apply_interaction(
            world,
            "char_arjun",
            "char_maya",
            delta_trust=-0.5,
            delta_affinity=-0.3,
            note="Maya caught concealing documents",
        )
        assert updated_rel.trust == round(initial_trust - 0.5, 2)
        assert "Maya caught concealing documents" in updated_rel.history

    def test_cooperation_increases_trust(self):
        """Test mutual cooperation raises trust and affinity within bounds"""
        world = create_demo_world()
        rel = RelationshipUpdater.apply_interaction(
            world,
            "char_arjun",
            "char_maya",
            delta_trust=0.4,
            delta_affinity=0.3,
            note="Shared crucial evidence safely",
        )
        assert rel.trust > 0.4
        assert rel.affinity > 0.4

    def test_threat_increases_fear_and_anger(self):
        """Test intimidation or threat escalates fear while respecting bounds [-1.0, 1.0]"""
        world = create_demo_world()
        maya = world.characters["char_maya"]

        EmotionUpdater.adjust_emotion(
            maya,
            delta_fear=0.4,
            delta_anger=0.3,
            delta_trust=-0.4,
        )

        assert maya.emotional_state.fear >= 0.9
        assert maya.emotional_state.anger >= 0.7

        # Push past maximum 1.0
        EmotionUpdater.adjust_emotion(maya, delta_fear=1.0)
        assert maya.emotional_state.fear == 1.0
