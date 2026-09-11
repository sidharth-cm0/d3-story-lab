"""Goal model representing character goals"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class GoalStatus(str, Enum):
    """Status of a goal"""

    ACTIVE = "active"
    COMPLETED = "completed"
    ACHIEVED = "achieved"
    BLOCKED = "blocked"
    ABANDONED = "abandoned"
    FAILED = "failed"


class Goal(BaseModel):
    """Represents a goal that a character wants to achieve"""

    id: str = Field(..., description="Unique goal ID")
    character_id: str = Field(..., description="Character who has this goal")
    description: str = Field(..., description="What the character wants to achieve")
    priority: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Priority: 0.0 (low) to 1.0 (critical)",
    )
    status: GoalStatus = Field(default=GoalStatus.ACTIVE)
    progress: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Progress toward achieving the goal: 0.0 to 1.0",
    )
    blocked_reason: Optional[str] = Field(None, description="Reason goal is blocked if any")
    last_progress_tick: Optional[int] = Field(None, description="Simulation tick of last progress")
    reason: Optional[str] = Field(None, description="Why they have this goal")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "goal_001",
                "character_id": "char_arjun",
                "description": "Recover the missing documents",
                "priority": 0.95,
                "status": "active",
                "reason": "They contain evidence needed for the case",
            }
        }
    )
