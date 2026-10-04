"""Tests for Scribe dialogue direct-address surface realization polish (Phase J5).

Validates that:
1. First direct address in a scene retains the full name.
2. Subsequent direct addresses in the same scene use the short/first name.
3. Event grounding (source_event_ids) remains 100% identical and traceable.
4. Zero changes to simulation, canonical WorldState, or knowledge firewall.
"""

from src.narrative.scribe import Scribe
from src.narrative.scene_projection import ObservableSceneProjection, ObservableBeat, ObservableDialogueLine, DramaticFunction, ObservableObjective
from src.narrative.fountain import ScreenplayBlockType


def test_dialogue_direct_address_polish_rule():
    scribe = Scribe()
    names = {"char_arjun": "Arjun Mehta", "char_evelyn": "Agent Evelyn"}
    counts = {}

    # Line 1: First address to Arjun
    line1 = "What do you know about the ledger, Arjun Mehta?"
    p1 = scribe.polish_dialogue_direct_address(line1, names, counts)
    assert p1 == "What do you know about the ledger, Arjun Mehta?"
    assert counts["char_arjun"] == 1

    # Line 2: Second address to Arjun in same scene
    line2 = "We need to leave immediately, Arjun Mehta."
    p2 = scribe.polish_dialogue_direct_address(line2, names, counts)
    assert p2 == "We need to leave immediately, Arjun."
    assert counts["char_arjun"] == 2

    # Line 3: Third address at start of sentence
    line3 = "Arjun Mehta, hand me the microdot."
    p3 = scribe.polish_dialogue_direct_address(line3, names, counts)
    assert p3 == "Arjun, hand me the microdot."

    # Line 4: First address to Evelyn (titled name "Agent Evelyn")
    line4 = "Where is the perimeter guard, Agent Evelyn?"
    p4 = scribe.polish_dialogue_direct_address(line4, names, counts)
    assert p4 == "Where is the perimeter guard, Agent Evelyn?"
    assert counts["char_evelyn"] == 1

    # Line 5: Second address to Evelyn uses title/short name
    line5 = "Agent Evelyn, the sirens are active."
    p5 = scribe.polish_dialogue_direct_address(line5, names, counts)
    assert p5 == "Evelyn, the sirens are active."
    assert counts["char_evelyn"] == 2


def test_dialogue_direct_address_preserves_strict_provenance():
    scribe = Scribe()
    proj = ObservableSceneProjection(
        scene_id="sc_test_polish",
        location_label="INT. ARCHIVES VAULT",
        time_label="NIGHT",
        characters_present=["char_arjun", "char_maya"],
        purpose=DramaticFunction.REVELATION,
        objective=ObservableObjective(
            pov_character_id="char_arjun",
            wants="retrieve cipher",
            obstacle="locked door",
            outcome="ACHIEVED",
        ),
        beats=[
            ObservableBeat(event_id="evt_d1", description="Arjun reaches for the safe.", characters_involved=["char_arjun"]),
            ObservableBeat(event_id="evt_d2", description="Maya turns to Arjun.", characters_involved=["char_maya"]),
        ],
        dialogue=[
            ObservableDialogueLine(
                source_event_id="evt_d1",
                speaker_id="char_maya",
                listener_ids=["char_arjun"],
                communicative_intent="TRUTHFUL",
                text="What do you know about the vault, Arjun Mehta?",
            ),
            ObservableDialogueLine(
                source_event_id="evt_d2",
                speaker_id="char_maya",
                listener_ids=["char_arjun"],
                communicative_intent="TRUTHFUL",
                text="Arjun Mehta, step away from the terminal.",
            ),
        ],
        source_event_ids=["evt_d1", "evt_d2"],
    )

    blocks = scribe.compose_scene_blocks(proj, character_names={"char_arjun": "Arjun Mehta", "char_maya": "Maya Lin"})

    dialogue_blocks = [b for b in blocks if b.element_type == "DIALOGUE"]
    assert len(dialogue_blocks) == 2

    # First line retains full name
    assert "Arjun Mehta" in dialogue_blocks[0].content
    # Second line polished to short name
    assert "Arjun," in dialogue_blocks[1].content
    assert "Arjun Mehta" not in dialogue_blocks[1].content

    # Strict provenance assertion: source_event_ids remain intact
    assert dialogue_blocks[0].source_event_ids == ["evt_d1"]
    assert dialogue_blocks[1].source_event_ids == ["evt_d2"]
