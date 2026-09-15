"""Story Structure Library: Canonical definitions, beats, and compatibility matrix.

Defines the 6 primary dramatic structures:
1. THREE_ACT (Classic dramatic arc: Setup, Confrontation, Resolution)
2. HERO_JOURNEY (Campbell/Vogler mythic archetype: Call, Ordeal, Return)
3. FREYTAG (Dramatic pyramid: Exposition, Rising Action, Climax, Falling Action, Catastrophe)
4. SAVE_THE_CAT (Snyder 15-beat screenplay structure with Midpoint and All is Lost)
5. STORY_CIRCLE (Harmon 8-stage circular journey: You, Need, Go, Search, Find, Take, Return, Change)
6. KISHOTENKETSU (Four-act East Asian structure: Introduction, Development, Twist, Harmonization - non-conflict driven)

COMPATIBILITY MATRIX:
Controls which secondary beat overlays can be meaningfully paired without narrative contradiction.
"""

from typing import Dict, List, Optional
from src.domain.story_structure import (
    StoryStructureType,
    BeatDefinition,
    StructureDefinition,
)

# Canonical beat definitions for each structure
THREE_ACT_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="3act_01_setup",
        name="Status Quo & Setup",
        act="Act I",
        target_position_pct=0.10,
        expected_dramatic_function="Establish primary character, environment, and underlying tension.",
        pressure_signal="Low environmental pressure; establish stakes and baseline behavior.",
        description="Introduces the focal characters in their baseline environment.",
    ),
    BeatDefinition(
        beat_id="3act_02_inciting",
        name="Inciting Incident",
        act="Act I",
        target_position_pct=0.18,
        expected_dramatic_function="Disrupt the status quo with an unavoidable challenge or arrival.",
        pressure_signal="Introduce an immediate objective or unexpected encounter.",
        description="An external event disrupts the initial balance.",
    ),
    BeatDefinition(
        beat_id="3act_03_plot_point_1",
        name="Plot Point 1 (Lock-In)",
        act="Act I",
        target_position_pct=0.25,
        expected_dramatic_function="Commit characters to the confrontation; point of no return.",
        pressure_signal="Block primary exit or impose a hard deadline.",
        description="The protagonist commits to a course of action with no easy retreat.",
    ),
    BeatDefinition(
        beat_id="3act_04_rising_action",
        name="Rising Confrontation",
        act="Act II",
        target_position_pct=0.38,
        expected_dramatic_function="Escalate obstacles and test initial strategies through tactical friction.",
        pressure_signal="Complicate information; inject opposing character resistance.",
        description="Characters pursue tactical sub-goals while complications multiply.",
    ),
    BeatDefinition(
        beat_id="3act_05_midpoint",
        name="Midpoint Reversal",
        act="Act II",
        target_position_pct=0.50,
        expected_dramatic_function="A major revelation or reversal shifts the nature of the conflict.",
        pressure_signal="Reveal a hidden secret or shift power balance between actors.",
        description="The stakes rise dramatically and the passive stance becomes active.",
    ),
    BeatDefinition(
        beat_id="3act_06_crisis",
        name="Crisis & All Hope Lost",
        act="Act II",
        target_position_pct=0.75,
        expected_dramatic_function="Maximum vulnerability; initial plan collapses under pressure.",
        pressure_signal="Peak obstacle pressure; force a difficult trade-off or confession.",
        description="The characters face seemingly insurmountable failure.",
    ),
    BeatDefinition(
        beat_id="3act_07_climax",
        name="Climax",
        act="Act III",
        target_position_pct=0.88,
        expected_dramatic_function="Decisive confrontation resolving the core dramatic question.",
        pressure_signal="Final high-stakes standoff; direct clash of goals.",
        description="Direct confrontation where the ultimate truth or possession is determined.",
    ),
    BeatDefinition(
        beat_id="3act_08_resolution",
        name="Resolution & Aftermath",
        act="Act III",
        target_position_pct=0.98,
        expected_dramatic_function="Establish the new normal and consequences of the outcome.",
        pressure_signal="Pacing settles; observe the transformed reality.",
        description="The aftermath of the climax settles into a transformed reality.",
    ),
]

HERO_JOURNEY_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="hero_01_ordinary_world",
        name="Ordinary World",
        act="Departure",
        target_position_pct=0.08,
        expected_dramatic_function="Depict normal reality before the disruption.",
        pressure_signal="Establish baseline capabilities and unfulfilled drive.",
        description="The protagonist within familiar surroundings.",
    ),
    BeatDefinition(
        beat_id="hero_02_call_to_adventure",
        name="Call to Adventure",
        act="Departure",
        target_position_pct=0.16,
        expected_dramatic_function="Present the challenge or mission that disrupts the ordinary.",
        pressure_signal="Introduce mission objective or external summons.",
        description="A problem or challenge that can no longer be ignored.",
    ),
    BeatDefinition(
        beat_id="hero_03_crossing_threshold",
        name="Crossing the First Threshold",
        act="Departure",
        target_position_pct=0.25,
        expected_dramatic_function="Enter the unfamiliar or perilous special world.",
        pressure_signal="Heighten environmental peril or unfamiliarity.",
        description="The hero crosses into the unfamiliar world with higher stakes.",
    ),
    BeatDefinition(
        beat_id="hero_04_tests_allies_enemies",
        name="Tests, Allies, and Enemies",
        act="Initiation",
        target_position_pct=0.45,
        expected_dramatic_function="Assess trust, navigate alliances, and overcome minor trials.",
        pressure_signal="Test character loyalty and probe hidden motives.",
        description="The hero encounters resistance and determines who can be trusted.",
    ),
    BeatDefinition(
        beat_id="hero_05_inmost_cave_ordeal",
        name="The Supreme Ordeal",
        act="Initiation",
        target_position_pct=0.65,
        expected_dramatic_function="Facing the greatest fear or central threat in the danger zone.",
        pressure_signal="Maximum acute danger; test character resolve against extinction.",
        description="Direct encounter with the central threat in deep peril.",
    ),
    BeatDefinition(
        beat_id="hero_06_reward",
        name="Seizing the Sword (Reward)",
        act="Initiation",
        target_position_pct=0.75,
        expected_dramatic_function="Claim the classified object, secret, or breakthrough.",
        pressure_signal="Temporary triumph; realization of the true cost.",
        description="The protagonist gains possession of the critical object or truth.",
    ),
    BeatDefinition(
        beat_id="hero_07_road_back",
        name="The Road Back",
        act="Return",
        target_position_pct=0.85,
        expected_dramatic_function="Urgent escape or pursuit as consequences trigger retaliation.",
        pressure_signal="Chase or escape pressure; exit route threatened.",
        description="Pursuit or urgent race to escape with the prize.",
    ),
    BeatDefinition(
        beat_id="hero_08_return_elixir",
        name="Resurrection & Return",
        act="Return",
        target_position_pct=0.98,
        expected_dramatic_function="Final test of the transformed self and arrival in new balance.",
        pressure_signal="Final stabilization; observe permanent transformation.",
        description="Return with the insight or prize that permanently transforms the world.",
    ),
]

FREYTAG_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="freytag_01_exposition",
        name="Exposition",
        act="Exposition",
        target_position_pct=0.15,
        expected_dramatic_function="Introduce the characters, context, and latent moral/power conflicts.",
        pressure_signal="Baseline atmospheric tension.",
        description="The initial situation and relationship tensions are mapped.",
    ),
    BeatDefinition(
        beat_id="freytag_02_inciting_force",
        name="Inciting Force",
        act="Rising Action",
        target_position_pct=0.25,
        expected_dramatic_function="Catalyst sets the escalating chain of cause and effect in motion.",
        pressure_signal="First direct confrontation or transaction.",
        description="A decisive event puts the tragic or dramatic chain in motion.",
    ),
    BeatDefinition(
        beat_id="freytag_03_rising_action",
        name="Rising Action",
        act="Rising Action",
        target_position_pct=0.45,
        expected_dramatic_function="Complications tighten the trap; characters commit deeper.",
        pressure_signal="Intensify suspicion and eliminate easy solutions.",
        description="Events build in tension and complexity toward the climax.",
    ),
    BeatDefinition(
        beat_id="freytag_04_climax",
        name="Climax / Turning Point",
        act="Climax",
        target_position_pct=0.60,
        expected_dramatic_function="The decisive point where the protagonist's fortunes turn irrevocably.",
        pressure_signal="Peak dramatic tension; irrecoverable choice.",
        description="The apex of dramatic conflict and fateful decision.",
    ),
    BeatDefinition(
        beat_id="freytag_05_falling_action",
        name="Falling Action",
        act="Falling Action",
        target_position_pct=0.80,
        expected_dramatic_function="Unraveling of consequences and desperate containment.",
        pressure_signal="Relentless consequence unfolding; escape slipping away.",
        description="The momentum of consequence moves toward the inescapable end.",
    ),
    BeatDefinition(
        beat_id="freytag_06_catastrophe_denouement",
        name="Catastrophe / Denouement",
        act="Denouement",
        target_position_pct=0.95,
        expected_dramatic_function="The final accounting, revelation of full cost, and closure.",
        pressure_signal="Cold stillness after the storm.",
        description="Final resolution and gravity of the outcome.",
    ),
]

SAVE_THE_CAT_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="stc_01_opening_image",
        name="Opening Image",
        act="Act 1",
        target_position_pct=0.05,
        expected_dramatic_function="Visual and tonal snapshot of the starting condition.",
        pressure_signal="Atmospheric framing of initial state.",
        description="A visual that represents the struggle and tone before change.",
    ),
    BeatDefinition(
        beat_id="stc_02_theme_stated",
        name="Theme Stated",
        act="Act 1",
        target_position_pct=0.10,
        expected_dramatic_function="Hint at the deeper thematic question beneath the immediate goal.",
        pressure_signal="Subtle philosophical or moral divergence between characters.",
        description="What the story is really about is spoken or foreshadowed.",
    ),
    BeatDefinition(
        beat_id="stc_03_catalyst",
        name="Catalyst",
        act="Act 1",
        target_position_pct=0.20,
        expected_dramatic_function="The disruptive event that breaks the opening world.",
        pressure_signal="Immediate surprise or arrival forcing response.",
        description="The telegram, knock on the door, or sudden discovery.",
    ),
    BeatDefinition(
        beat_id="stc_04_break_into_two",
        name="Break into Two",
        act="Act 2A",
        target_position_pct=0.28,
        expected_dramatic_function="Protagonist steps into an active attempt to solve the problem.",
        pressure_signal="Lock into new arena of operation.",
        description="Entering the upside-down world of Act 2.",
    ),
    BeatDefinition(
        beat_id="stc_05_midpoint",
        name="Midpoint",
        act="Act 2A",
        target_position_pct=0.50,
        expected_dramatic_function="False victory or false defeat; stakes escalate from public to personal.",
        pressure_signal="Flip the tactical advantage between actors.",
        description="A major turn where the stakes are raised significantly.",
    ),
    BeatDefinition(
        beat_id="stc_06_all_is_lost",
        name="All is Lost",
        act="Act 2B",
        target_position_pct=0.75,
        expected_dramatic_function="Apparent death of the goal; old coping mechanisms completely exhausted.",
        pressure_signal="Expose deepest vulnerability or betrayal.",
        description="The whiff of death and total apparent collapse.",
    ),
    BeatDefinition(
        beat_id="stc_07_break_into_three",
        name="Break into Three",
        act="Act 3",
        target_position_pct=0.85,
        expected_dramatic_function="A new insight synthesizes character need and objective goal.",
        pressure_signal="Clarify ultimate leverage.",
        description="The protagonist finds the true solution from the lesson learned.",
    ),
    BeatDefinition(
        beat_id="stc_08_finale_final_image",
        name="Finale & Final Image",
        act="Act 3",
        target_position_pct=0.98,
        expected_dramatic_function="Execute the climactic synthesis and present the transformed world.",
        pressure_signal="Final resolution and closing snapshot.",
        description="Climactic proof of change and mirror to the opening image.",
    ),
]

STORY_CIRCLE_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="circle_01_you",
        name="1. You (Comfort Zone)",
        act="Zone 1",
        target_position_pct=0.12,
        expected_dramatic_function="A character is in a zone of comfort.",
        pressure_signal="Low urgency; showcase regular routine.",
        description="Protagonist in their natural habitat.",
    ),
    BeatDefinition(
        beat_id="circle_02_need",
        name="2. Need (Desire)",
        act="Zone 1",
        target_position_pct=0.25,
        expected_dramatic_function="A character wants or lacks something vital.",
        pressure_signal="Sharpen the internal or external longing.",
        description="The need becomes intolerable.",
    ),
    BeatDefinition(
        beat_id="circle_03_go",
        name="3. Go (Cross Threshold)",
        act="Zone 2",
        target_position_pct=0.38,
        expected_dramatic_function="Enter an unfamiliar situation or hostile territory.",
        pressure_signal="Entering unknown terrain with hidden risks.",
        description="Entering the unknown world to satisfy the need.",
    ),
    BeatDefinition(
        beat_id="circle_04_search",
        name="4. Search (Adaptation)",
        act="Zone 2",
        target_position_pct=0.50,
        expected_dramatic_function="Adapt to tests, friction, and tactical trial.",
        pressure_signal="Increasing obstacles requiring tactical improvisation.",
        description="Struggling to adapt to the new reality.",
    ),
    BeatDefinition(
        beat_id="circle_05_find",
        name="5. Find (Get What They Wanted)",
        act="Zone 3",
        target_position_pct=0.62,
        expected_dramatic_function="Locate the object, secret, or breakthrough.",
        pressure_signal="The objective is touched; trap is sprung.",
        description="Attaining the object of desire.",
    ),
    BeatDefinition(
        beat_id="circle_06_take",
        name="6. Take (Pay Heavy Price)",
        act="Zone 3",
        target_position_pct=0.75,
        expected_dramatic_function="Pay a steep price for possession.",
        pressure_signal="Consequence enforcement; heavy cost demanded.",
        description="Paying the toll for what was taken.",
    ),
    BeatDefinition(
        beat_id="circle_07_return",
        name="7. Return (Bring It Back)",
        act="Zone 4",
        target_position_pct=0.88,
        expected_dramatic_function="Return back toward the familiar world with the prize.",
        pressure_signal="Urgent transit while bearing the burden.",
        description="Returning across the threshold.",
    ),
    BeatDefinition(
        beat_id="circle_08_change",
        name="8. Change (Having Transformed)",
        act="Zone 4",
        target_position_pct=0.98,
        expected_dramatic_function="The protagonist is fundamentally altered by the cycle.",
        pressure_signal="Closure on the transformed reality.",
        description="The world or the protagonist is permanently different.",
    ),
]

KISHOTENKETSU_BEATS: List[BeatDefinition] = [
    BeatDefinition(
        beat_id="kisho_01_ki",
        name="Ki (Introduction)",
        act="Ki",
        target_position_pct=0.25,
        expected_dramatic_function="Introduce characters, setting, and daily reality without immediate confrontation.",
        pressure_signal="Zero artificial conflict; allow characters natural observation.",
        description="Presents the starting picture calmly and thoroughly.",
    ),
    BeatDefinition(
        beat_id="kisho_02_sho",
        name="Sho (Development)",
        act="Sho",
        target_position_pct=0.50,
        expected_dramatic_function="Develop and elaborate upon the elements introduced in Ki.",
        pressure_signal="Deepen observation, dialogue, and interaction without weaponized stakes.",
        description="Follows naturally from Ki, expanding details and context.",
    ),
    BeatDefinition(
        beat_id="kisho_03_ten",
        name="Ten (Twist / Unexpected Perspective)",
        act="Ten",
        target_position_pct=0.75,
        expected_dramatic_function="Introduce an unexpected, seemingly disconnected element or jarring perspective shift.",
        pressure_signal="Introduce an orthogonal fact, surprise witness, or hidden dimension.",
        description="A turn that seems unrelated or startling, recontextualizing everything.",
    ),
    BeatDefinition(
        beat_id="kisho_04_ketsu",
        name="Ketsu (Harmonization / Conclusion)",
        act="Ketsu",
        target_position_pct=0.95,
        expected_dramatic_function="Bring the unexpected twist (Ten) and original elements (Ki/Sho) into meaningful synthesis.",
        pressure_signal="Synthesize connections; reconcile disparate observations.",
        description="Shows how the twist connects back to the beginning, yielding an emergent insight.",
    ),
]

STRUCTURE_DEFINITIONS: Dict[StoryStructureType, StructureDefinition] = {
    StoryStructureType.THREE_ACT: StructureDefinition(
        structure_type=StoryStructureType.THREE_ACT,
        display_name="Three-Act Dramatic Structure",
        description="Classic narrative progression moving through Setup, Confrontation, and Resolution with rising stakes.",
        genre_affinities=["thriller", "noir", "espionage", "drama", "crime", "investigation", "suspense"],
        tone_affinities=["tense", "gritty", "urgent", "focused", "deliberate"],
        conflict_types=["interpersonal", "conspiracy", "deadline", "heist", "investigation"],
        beats=THREE_ACT_BEATS,
        compatible_secondary_structures=[
            StoryStructureType.SAVE_THE_CAT,
            StoryStructureType.STORY_CIRCLE,
        ],
    ),
    StoryStructureType.HERO_JOURNEY: StructureDefinition(
        structure_type=StoryStructureType.HERO_JOURNEY,
        display_name="Hero's Journey (Monomyth)",
        description="Archetypal transformation through crossing thresholds, deep trials, obtaining the prize, and return.",
        genre_affinities=["mythic", "adventure", "espionage", "transformation", "survival"],
        tone_affinities=["epic", "determined", "revelatory", "solemn"],
        conflict_types=["moral_test", "inmost_fear", "quest", "initiation"],
        beats=HERO_JOURNEY_BEATS,
        compatible_secondary_structures=[
            StoryStructureType.THREE_ACT,
        ],
    ),
    StoryStructureType.FREYTAG: StructureDefinition(
        structure_type=StoryStructureType.FREYTAG,
        display_name="Freytag's Dramatic Pyramid",
        description="Rigorous dramatic rise to a central turning point, followed by irreversible falling action and catastrophe.",
        genre_affinities=["tragedy", "noir", "psychological_drama", "betrayal", "existential"],
        tone_affinities=["fatalistic", "claustrophobic", "somber", "inevitable"],
        conflict_types=["inevitable_downfall", "hubris", "betrayal", "moral_compromise"],
        beats=FREYTAG_BEATS,
        compatible_secondary_structures=[
            StoryStructureType.THREE_ACT,
        ],
    ),
    StoryStructureType.SAVE_THE_CAT: StructureDefinition(
        structure_type=StoryStructureType.SAVE_THE_CAT,
        display_name="Save the Cat (Screenplay Beat Sheet)",
        description="Pacing-optimized modern cinematic structure with precise catalysts, midpoints, and 'All is Lost' crisis.",
        genre_affinities=["cinematic_thriller", "action", "heist", "mystery", "crime"],
        tone_affinities=["sharp", "propulsive", "cinematic", "dynamic"],
        conflict_types=["ticking_clock", "heist", "tactical_cat_and_mouse"],
        beats=SAVE_THE_CAT_BEATS,
        compatible_secondary_structures=[
            StoryStructureType.THREE_ACT,
        ],
    ),
    StoryStructureType.STORY_CIRCLE: StructureDefinition(
        structure_type=StoryStructureType.STORY_CIRCLE,
        display_name="Dan Harmon's Story Circle",
        description="Character-driven cyclical transformation: You, Need, Go, Search, Find, Take, Return, Change.",
        genre_affinities=["character_study", "noir", "psychological", "procedural"],
        tone_affinities=["introspective", "ironic", "grounded"],
        conflict_types=["internal_void", "unintended_consequence", "moral_cost"],
        beats=STORY_CIRCLE_BEATS,
        compatible_secondary_structures=[
            StoryStructureType.THREE_ACT,
        ],
    ),
    StoryStructureType.KISHOTENKETSU: StructureDefinition(
        structure_type=StoryStructureType.KISHOTENKETSU,
        display_name="Kishōtenketsu (Four-Part Synthesis)",
        description="Non-conflict-centric structure based on Introduction, Development, Twist, and Harmonization.",
        genre_affinities=["contemplative", "surreal", "slice_of_life", "philosophical", "mystery"],
        tone_affinities=["observational", "poetic", "quiet", "subtle"],
        conflict_types=["perspective_shift", "harmony_disruption", "unrelated_synthesis"],
        beats=KISHOTENKETSU_BEATS,
        compatible_secondary_structures=[],  # Explicitly NO conflict-centric overlay by default
    ),
}

# Compatibility mapping helper
def get_compatible_secondary_structures(primary: StoryStructureType) -> List[StoryStructureType]:
    """Return list of valid secondary structures for a primary structure."""
    defn = STRUCTURE_DEFINITIONS.get(primary)
    if not defn:
        return []
    return list(defn.compatible_secondary_structures)


def is_structure_pair_compatible(primary: StoryStructureType, secondary: StoryStructureType) -> bool:
    """Check whether a primary and secondary structure pairing is canonically permitted."""
    if primary == secondary:
        return False
    return secondary in get_compatible_secondary_structures(primary)


# Canonical exports
STRUCTURE_LIBRARY = STRUCTURE_DEFINITIONS
COMPATIBILITY_MATRIX: Dict[tuple, bool] = {
    (p, s): is_structure_pair_compatible(p, s)
    for p in StoryStructureType
    for s in StoryStructureType
}

