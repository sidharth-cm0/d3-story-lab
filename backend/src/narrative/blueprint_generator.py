"""Story Blueprint Generator for D3 Story Lab.

Generates soft narrative blueprints containing:
- Theme, dramatic question, stakes
- Expected beat sheet with expected dramatic functions and pressure signals
- Pacing recommendations for the Director agent

CRITICAL RULE: STRUCTURE WITHOUT PUPPETRY
A StoryBlueprint NEVER contains forced dialogue, forced exact character actions,
or a hidden finished script. Characters retain full autonomy.
"""

from typing import Optional, Dict, Any
from src.domain.story_structure import (
    StoryStructureType,
    PresentationStrategy,
    StoryBlueprint,
    StructureSelectionResult,
)
from src.narrative.structure_library import STRUCTURE_DEFINITIONS


class StoryBlueprintGenerator:
    """Creates soft dramatic blueprints from premise analysis and selected structure."""

    def __init__(self, provider: Optional[Any] = None):
        self.provider = provider

    def generate_blueprint(
        self,
        prompt: str,
        selection: StructureSelectionResult,
        title: Optional[str] = None,
        presentation_strategy: PresentationStrategy = PresentationStrategy.CHRONOLOGICAL,
    ) -> StoryBlueprint:
        """Create a soft StoryBlueprint with expected dramatic functions and pressure signals."""
        primary = selection.primary_structure
        defn = STRUCTURE_DEFINITIONS[primary]

        prompt_lower = prompt.lower()

        # Derive thematic question & stakes from prompt
        if "dossier" in prompt_lower or "classified" in prompt_lower or "spy" in prompt_lower:
            theme = "The cost of loyalty and the vulnerability of secrets under pressure."
            dramatic_question = "Will the truth be secured before the exit is permanently compromised?"
            stakes = "Exposure of classified operational intelligence and loss of operative cover."
        elif "murder" in prompt_lower or "crime" in prompt_lower or "detective" in prompt_lower:
            theme = "Justice versus self-preservation in an environment of deception."
            dramatic_question = "Can the investigator uncover the truth without becoming complicit?"
            stakes = "Survival, moral integrity, and legal accountability."
        elif "heist" in prompt_lower or "stolen" in prompt_lower or "vault" in prompt_lower:
            theme = "Trust is a currency that depreciates under deadline pressure."
            dramatic_question = "Will the alliance hold together until the objective is extracted?"
            stakes = "Capture, imprisonment, and betrayal."
        else:
            theme = "Emergence of truth through high-stakes interpersonal friction."
            dramatic_question = "How will the characters adapt when their private agendas collide?"
            stakes = "Personal autonomy, vital secrets, and relationship trust."

        story_title = title or "THE RECOVERY PROTOCOL"

        # Copy canonical expected beats as soft constraints
        expected_beats = list(defn.beats)

        soft_constraints = {
            "tone": "Noir / Psychological Suspense",
            "pacing_guideline": "Deliberate setup escalating to high-frequency tactical standoff.",
            "allowed_interventions": [
                "environmental_distraction",
                "security_patrol_audio",
                "time_pressure_signal",
                "power_grid_flicker",
            ],
            "director_instruction": "Inject external atmospheric pressure only; do not force character choices or dialogue.",
        }

        blueprint = StoryBlueprint(
            story_title=story_title,
            primary_structure=primary,
            secondary_structure=selection.secondary_structure,
            presentation_strategy=presentation_strategy,
            theme=theme,
            dramatic_question=dramatic_question,
            stakes=stakes,
            expected_beats=expected_beats,
            soft_constraints=soft_constraints,
            metadata={
                "selection_mode": selection.selection_mode.value,
                "fit_score": selection.fit_score,
                "fit_rationale": selection.fit_rationale,
            },
        )

        self.assert_blueprint_is_soft(blueprint)
        return blueprint

    @staticmethod
    def assert_blueprint_is_soft(blueprint: StoryBlueprint) -> None:
        """Enforces the non-negotiable rule: STRUCTURE WITHOUT PUPPETRY.

        Raises ValueError if blueprint contains forced dialogue, forced character decisions,
        or hard scripted outcomes.
        """
        raw_dict = blueprint.model_dump(mode="json")
        dump_str = str(raw_dict).lower()

        forbidden_keys = [
            "forced_dialogue",
            "scripted_lines",
            "forced_actions",
            "must_say",
            "must_do",
            "character_script",
            "predetermined_winner",
        ]

        for fk in forbidden_keys:
            if fk in dump_str:
                raise ValueError(f"Architectural Rule Violation: Blueprint contains puppetry key '{fk}'.")

        # Confirm all beats contain only soft dramatic functions and pressure signals
        for beat in blueprint.expected_beats:
            assert beat.expected_dramatic_function, "Beat must specify expected dramatic function"
            assert beat.pressure_signal, "Beat must specify pressure signal"
