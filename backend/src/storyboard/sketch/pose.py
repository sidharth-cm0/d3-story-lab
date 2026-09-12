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
    QUESTIONING = "QUESTIONING"
    EVASIVE = "EVASIVE"
    SEARCHING = "SEARCHING"


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
    """Geometric joint configuration and gestural dynamics for a pose."""
    model_config = ConfigDict(extra="ignore")

    pose_type: PoseType
    head_tilt_deg: float = 0.0
    torso_angle_deg: float = 0.0
    spine_bend: float = 0.0
    # Gestural Dynamics (Section 3 & 15)
    shoulder_tilt: float = 0.0      # Deg tilt: positive = right shoulder higher
    hip_tilt: float = 0.0           # Deg tilt: counter-tilt to shoulders (contrapposto)
    spine_curve: float = 0.0        # Curvature factor for line of action (-1.0 to 1.0)
    weight_leg: str = "balanced"    # "left", "right", or "balanced"
    balance_point: float = 0.0      # Horizontal shift of center of gravity
    arm_foreshortening: float = 1.0 # Scale multiplier for arm pointing toward camera
    leg_foreshortening: float = 1.0 # Scale multiplier for leg running toward camera

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
        shoulder_tilt=-8.0,
        hip_tilt=10.0,
        spine_curve=0.35,
        weight_leg="right",
        balance_point=0.45,
        leg_foreshortening=1.25,
        arm_foreshortening=1.20,
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
        shoulder_tilt=6.0,
        hip_tilt=-4.0,
        spine_curve=0.20,
        weight_leg="left",
        balance_point=0.10,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.20), hand=(-0.06, 0.28)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.28, 0.12), hand=(0.46, 0.10)),  # Arm extended with beam
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.10, 0.28), foot=(-0.12, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.12, 0.28), foot=(0.16, 0.56)),
        hand_interaction_point=(0.46, 0.10),
    ),
    PoseType.QUESTIONING: PoseDefinition(
        pose_type=PoseType.QUESTIONING,
        head_tilt_deg=8.0,
        torso_angle_deg=7.0,  # Torso slightly forward
        shoulder_tilt=10.0,   # One shoulder higher
        hip_tilt=-5.0,        # Contrapposto counter-tilt
        spine_curve=0.18,
        weight_leg="left",
        balance_point=0.12,
        arm_foreshortening=1.20,
        left_arm=LimbJoints(shoulder=(-0.14, 0.02), elbow=(-0.18, 0.22), hand=(-0.14, 0.40)),
        right_arm=LimbJoints(shoulder=(0.14, -0.04), elbow=(0.26, 0.12), hand=(0.34, 0.08)),  # Hand gesturing forward
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.08, 0.28), foot=(-0.08, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.10, 0.26), foot=(0.14, 0.54)),
    ),
    PoseType.DEFENSIVE: PoseDefinition(
        pose_type=PoseType.DEFENSIVE,
        head_tilt_deg=-8.0,
        torso_angle_deg=-14.0,  # Body leaned back
        shoulder_tilt=-8.0,
        hip_tilt=6.0,
        spine_curve=-0.25,
        weight_leg="left",      # Weight back
        balance_point=-0.16,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.20, 0.10), hand=(-0.06, 0.06)),  # Guarding chest
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.20, 0.12), hand=(0.08, 0.08)),   # Partially raised
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.16, 0.26), foot=(-0.20, 0.52)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.04, 0.28), foot=(0.02, 0.56)),
    ),
    PoseType.EVASIVE: PoseDefinition(
        pose_type=PoseType.EVASIVE,
        head_tilt_deg=-12.0,    # Head turned slightly away
        torso_angle_deg=-6.0,
        shoulder_tilt=8.0,      # Shoulder asymmetry
        hip_tilt=-4.0,
        spine_curve=-0.14,
        weight_leg="left",
        balance_point=-0.08,
        facing_direction=-0.4,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.20), hand=(-0.12, 0.36)),
        right_arm=LimbJoints(shoulder=(0.14, -0.02), elbow=(0.16, 0.18), hand=(0.08, 0.30)),
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.06, 0.28), foot=(-0.04, 0.56)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.12, 0.26), foot=(0.16, 0.54)),
    ),
    PoseType.SEARCHING: PoseDefinition(
        pose_type=PoseType.SEARCHING,
        head_tilt_deg=18.0,     # Head lowered
        torso_angle_deg=16.0,   # Torso bent forward
        shoulder_tilt=6.0,
        hip_tilt=-5.0,
        spine_curve=0.28,
        weight_leg="right",
        balance_point=0.20,
        left_arm=LimbJoints(shoulder=(-0.14, 0.0), elbow=(-0.16, 0.18), hand=(-0.08, 0.28)),
        right_arm=LimbJoints(shoulder=(0.14, 0.0), elbow=(0.32, 0.10), hand=(0.52, 0.08)),  # Extended flashlight/arm reach
        left_leg=LegJoints(hip=(-0.08, 0.0), knee=(-0.12, 0.28), foot=(-0.14, 0.55)),
        right_leg=LegJoints(hip=(0.08, 0.0), knee=(0.14, 0.26), foot=(0.18, 0.54)),
        hand_interaction_point=(0.52, 0.08),
    ),
}


def calculate_gesture_dynamics(pose_type: PoseType, facing_direction: float = 1.0) -> Dict[str, Any]:
    """Calculate gestural pose dynamics per Section 3:
    - line_of_action
    - shoulder_tilt
    - hip_tilt
    - spine_curve
    - weight_leg
    - balance_point
    - arm/leg foreshortening
    """
    pose = POSE_DEFINITIONS.get(pose_type, POSE_DEFINITIONS[PoseType.NEUTRAL])
    effective_facing = 1.0 if facing_direction >= 0 else -1.0
    return {
        "line_of_action": (
            (0.0, 0.0),
            (pose.torso_angle_deg * 0.4 * effective_facing, 0.5),
            (pose.balance_point * 20.0 * effective_facing, 1.0),
        ),
        "shoulder_tilt": pose.shoulder_tilt * effective_facing,
        "hip_tilt": pose.hip_tilt * effective_facing,
        "spine_curve": pose.spine_curve * effective_facing,
        "weight_leg": pose.weight_leg,
        "balance_point": pose.balance_point * effective_facing,
        "arm_foreshortening": pose.arm_foreshortening,
        "leg_foreshortening": pose.leg_foreshortening,
    }


def map_action_to_pose(action_text: str, dialogue_text: str = "", shot_purpose: str = "") -> PoseType:
    """Map screenplay narrative verbs, dialogue cues, and shot purpose to a defined pose."""
    text = (action_text + " " + dialogue_text + " " + shot_purpose).lower()

    if any(k in text for k in ["question", "interrogate", "demands", "confronts", "probes"]):
        return PoseType.QUESTIONING
    if any(k in text for k in ["lie", "lying", "lies", "evasive", "glances toward", "glance toward", "deceive"]):
        return PoseType.EVASIVE
    if any(k in text for k in ["search", "searches", "searching", "scours", "scanning"]):
        return PoseType.SEARCHING
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
