"""Pose library and action mapping for storyboard sketch characters.

Defines joint angles, limbs, gestures, and mappings from screenplay actions to poses.
"""

from __future__ import annotations
import re
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel, ConfigDict, Field


class PoseType(str, Enum):
    """Storyboard character pose postures."""
    NEUTRAL = "NEUTRAL"
    WALKING = "WALKING"
    RUNNING = "RUNNING"
    TURNING = "TURNING"
    SITTING = "SITTING"
    LEANING = "LEANING"
    POINTING = "POINTING"
    HOLDING_OBJECT = "HOLDING_OBJECT"
    EXAMINING_OBJECT = "EXAMINING_OBJECT"
    OPENING_DOOR = "OPENING_DOOR"
    REACHING = "REACHING"
    TALKING = "TALKING"
    DEFENSIVE = "DEFENSIVE"
    ANGRY = "ANGRY"
    SHOCKED = "SHOCKED"
    CROUCHING = "CROUCHING"
    LOOKING_BACK = "LOOKING_BACK"
    USING_PHONE = "USING_PHONE"
    AIMING_FLASHLIGHT = "AIMING_FLASHLIGHT"


class LimbJoints(BaseModel):
    """Normalized relative offsets for joints (normalized to character height)."""
    model_config = ConfigDict(extra="ignore")

    # Joint positions relative to root shoulder/hip
    shoulder: Tuple[float, float] = (0.0, 0.0)
    elbow: Tuple[float, float] = (0.0, 0.25)
    hand: Tuple[float, float] = (0.0, 0.50)


class LegJoints(BaseModel):
    """Normalized relative offsets for leg joints."""
    model_config = ConfigDict(extra="ignore")

    hip: Tuple[float, float] = (0.0, 0.0)
    knee: Tuple[float, float] = (0.0, 0.3)
    foot: Tuple[float, float] = (0.0, 0.6)


class PoseDefinition(BaseModel):
    """Geometric joint configuration for a pose."""
    model_config = ConfigDict(extra="ignore")

    pose_type: PoseType
    head_tilt_deg: float = 0.0
    torso_angle_deg: float = 0.0
    spine_bend: float = 0.0
    left_arm: LimbJoints = Field(default_factory=LimbJoints)
    right_arm: LimbJoints = Field(default_factory=LimbJoints)
    left_leg: LegJoints = Field(default_factory=LegJoints)
    right_leg: LegJoints = Field(default_factory=LegJoints)
    facing_direction: float = 1.0  # 1.0 right, -1.0 left, 0.0 front
    hand_interaction_point: Optional[Tuple[float, float]] = None
    is_seated: bool = False
    is_crouching: bool = False
    motion_blur_lines: bool = False


# Library of joint geometries
POSE_DEFINITIONS: Dict[PoseType, PoseDefinition] = {
    PoseType.NEUTRAL: PoseDefinition(
        pose_type=PoseType.NEUTRAL,
        head_tilt_deg=0.0,
        torso_angle_deg=0.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.15, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.15, 0.22), hand=(0.12, 0.44)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
    ),
    PoseType.WALKING: PoseDefinition(
        pose_type=PoseType.WALKING,
        head_tilt_deg=4.0,
        torso_angle_deg=5.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.22, 0.18), hand=(-0.26, 0.36)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.05, 0.20), hand=(-0.02, 0.38)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.18, 0.26), foot=(-0.24, 0.54)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.16, 0.24), foot=(0.22, 0.52)),
    ),
    PoseType.RUNNING: PoseDefinition(
        pose_type=PoseType.RUNNING,
        head_tilt_deg=10.0,
        torso_angle_deg=18.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.32, 0.12), hand=(-0.40, 0.02)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.28, 0.22), hand=(0.36, 0.38)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.30, 0.22), foot=(-0.42, 0.46)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.26, 0.18), foot=(0.38, 0.40)),
        motion_blur_lines=True,
    ),
    PoseType.TURNING: PoseDefinition(
        pose_type=PoseType.TURNING,
        head_tilt_deg=-12.0,
        torso_angle_deg=-8.0,
        facing_direction=-0.5,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.10, 0.20), hand=(-0.05, 0.38)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.22, 0.20), hand=(0.18, 0.40)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.05, 0.28), foot=(0.0, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.14, 0.26), foot=(0.18, 0.54)),
    ),
    PoseType.SITTING: PoseDefinition(
        pose_type=PoseType.SITTING,
        head_tilt_deg=-2.0,
        torso_angle_deg=-4.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.18, 0.18), hand=(-0.08, 0.26)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.18, 0.18), hand=(0.08, 0.26)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.18, 0.12), foot=(-0.18, 0.38)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.18, 0.12), foot=(0.18, 0.38)),
        is_seated=True,
    ),
    PoseType.LEANING: PoseDefinition(
        pose_type=PoseType.LEANING,
        head_tilt_deg=5.0,
        torso_angle_deg=8.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.25, 0.18), hand=(-0.22, 0.32)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.10, 0.24), hand=(0.06, 0.44)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.04, 0.28), foot=(-0.02, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.16, 0.26), foot=(0.20, 0.53)),
    ),
    PoseType.POINTING: PoseDefinition(
        pose_type=PoseType.POINTING,
        head_tilt_deg=6.0,
        torso_angle_deg=5.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.32, 0.04), hand=(0.54, 0.02)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.10, 0.28), foot=(-0.12, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.10, 0.28), foot=(0.14, 0.55)),
    ),
    PoseType.HOLDING_OBJECT: PoseDefinition(
        pose_type=PoseType.HOLDING_OBJECT,
        head_tilt_deg=8.0,
        torso_angle_deg=3.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.18, 0.18), hand=(-0.05, 0.24)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.20, 0.18), hand=(0.08, 0.24)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
        hand_interaction_point=(0.02, 0.24),
    ),
    PoseType.EXAMINING_OBJECT: PoseDefinition(
        pose_type=PoseType.EXAMINING_OBJECT,
        head_tilt_deg=18.0,  # Looking down intently
        torso_angle_deg=10.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.14, 0.16), hand=(-0.02, 0.18)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.16, 0.16), hand=(0.06, 0.18)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
        hand_interaction_point=(0.02, 0.18),
    ),
    PoseType.OPENING_DOOR: PoseDefinition(
        pose_type=PoseType.OPENING_DOOR,
        head_tilt_deg=4.0,
        torso_angle_deg=8.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.28, 0.16), hand=(0.42, 0.22)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.10, 0.28), foot=(-0.12, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.14, 0.26), foot=(0.18, 0.54)),
        hand_interaction_point=(0.42, 0.22),
    ),
    PoseType.REACHING: PoseDefinition(
        pose_type=PoseType.REACHING,
        head_tilt_deg=10.0,
        torso_angle_deg=12.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.12, 0.20), hand=(-0.08, 0.38)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.32, 0.10), hand=(0.48, 0.14)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.12, 0.28), foot=(-0.14, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.14, 0.26), foot=(0.18, 0.54)),
        hand_interaction_point=(0.48, 0.14),
    ),
    PoseType.TALKING: PoseDefinition(
        pose_type=PoseType.TALKING,
        head_tilt_deg=6.0,
        torso_angle_deg=4.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.24, 0.16), hand=(0.18, 0.10)),  # Expressive gesture
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
    ),
    PoseType.DEFENSIVE: PoseDefinition(
        pose_type=PoseType.DEFENSIVE,
        head_tilt_deg=-8.0,
        torso_angle_deg=-12.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.18, 0.10), hand=(-0.04, 0.08)),  # Guarding chest/face
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.18, 0.12), hand=(0.06, 0.08)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.14, 0.26), foot=(-0.18, 0.52)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.06, 0.28), foot=(0.04, 0.56)),
    ),
    PoseType.ANGRY: PoseDefinition(
        pose_type=PoseType.ANGRY,
        head_tilt_deg=8.0,
        torso_angle_deg=8.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.22, 0.18), hand=(-0.18, 0.36)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.26, 0.12), hand=(0.32, 0.02)),  # Fist or sharp point
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.12, 0.28), foot=(-0.14, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.12, 0.28), foot=(0.16, 0.56)),
    ),
    PoseType.SHOCKED: PoseDefinition(
        pose_type=PoseType.SHOCKED,
        head_tilt_deg=-10.0,
        torso_angle_deg=-6.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.24, 0.14), hand=(-0.16, 0.02)),  # Hands raised back
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.24, 0.14), hand=(0.16, 0.02)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.10, 0.28), foot=(-0.12, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.10, 0.28), foot=(0.12, 0.56)),
    ),
    PoseType.CROUCHING: PoseDefinition(
        pose_type=PoseType.CROUCHING,
        head_tilt_deg=12.0,
        torso_angle_deg=22.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.16), hand=(-0.10, 0.30)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.16, 0.16), hand=(0.10, 0.30)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.18, 0.16), foot=(-0.12, 0.32)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.18, 0.16), foot=(0.12, 0.32)),
        is_crouching=True,
    ),
    PoseType.LOOKING_BACK: PoseDefinition(
        pose_type=PoseType.LOOKING_BACK,
        head_tilt_deg=-25.0,  # Looking back over shoulder
        torso_angle_deg=5.0,
        facing_direction=-0.8,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.15, 0.22), hand=(0.12, 0.44)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
    ),
    PoseType.USING_PHONE: PoseDefinition(
        pose_type=PoseType.USING_PHONE,
        head_tilt_deg=12.0,
        torso_angle_deg=2.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.22), hand=(-0.12, 0.44)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.20, 0.14), hand=(0.10, -0.06)),  # To ear
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.08, 0.28), foot=(0.08, 0.56)),
        hand_interaction_point=(0.10, -0.06),
    ),
    PoseType.AIMING_FLASHLIGHT: PoseDefinition(
        pose_type=PoseType.AIMING_FLASHLIGHT,
        head_tilt_deg=6.0,
        torso_angle_deg=8.0,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.20), hand=(-0.06, 0.28)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.28, 0.12), hand=(0.46, 0.10)),  # Arm extended with beam
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.10, 0.28), foot=(-0.12, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.12, 0.28), foot=(0.16, 0.56)),
        hand_interaction_point=(0.46, 0.10),
    ),
}


def map_action_to_pose(action_text: str, dialogue_text: str = "", shot_purpose: str = "") -> PoseType:
    """Map screenplay narrative verbs, dialogue cues, and shot purpose to a defined pose."""
    text = (action_text + " " + dialogue_text + " " + shot_purpose).lower()

    if any(k in text for k in ["flashlight", "beam of light", "aims torch", "torch"]):
        return PoseType.AIMING_FLASHLIGHT
    if any(k in text for k in ["phone", "call", "dial", "receiver", "transceiver"]):
        return PoseType.USING_PHONE
    if any(k in text for k in ["reach", "takes", "picks up", "grabs", "reaches for"]):
        return PoseType.REACHING
    if any(k in text for k in ["examine", "inspect", "reads", "studies"]):
        return PoseType.EXAMINING_OBJECT
    if any(k in text for k in ["dossier", "ledger"]):
        return PoseType.EXAMINING_OBJECT
    if any(k in text for k in ["door", "unlocks", "opens door", "pushes open"]):
        return PoseType.OPENING_DOOR
    if any(k in text for k in ["run", "sprint", "flee", "escapes", "dashes"]):
        return PoseType.RUNNING
    if any(k in text for k in ["walk", "enters", "steps into", "approaches", "paces"]):
        return PoseType.WALKING
    if any(k in text for k in ["turns toward", "turns around", "spins", "pivots"]):
        return PoseType.TURNING
    if any(k in text for k in ["look back", "glances back", "behind him", "behind her"]):
        return PoseType.LOOKING_BACK
    if any(k in text for k in ["crouch", "kneel", "ducks", "hides under"]):
        return PoseType.CROUCHING
    if any(k in text for k in ["point", "gestures toward", "indicates"]):
        return PoseType.POINTING
    if any(k in text for k in ["hold", "carries", "gripping"]):
        return PoseType.HOLDING_OBJECT
    if any(k in text for k in ["sit", "chair", "desk", "seated"]):
        return PoseType.SITTING
    if any(k in text for k in ["lean", "slumps against", "wall"]):
        return PoseType.LEANING
    if any(k in text for k in ["shock", "freeze", "gasp", "stares in disbelief"]):
        return PoseType.SHOCKED
    if any(k in text for k in ["angry", "shouts", "slams", "threat", "furious"]):
        return PoseType.ANGRY
    if any(k in text for k in ["defend", "recoils", "backs away", "guards"]):
        return PoseType.DEFENSIVE
    if dialogue_text or "dialogue" in text or "speaks" in text:
        return PoseType.TALKING

    return PoseType.NEUTRAL
