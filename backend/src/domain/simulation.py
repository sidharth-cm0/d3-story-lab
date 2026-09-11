"""Simulation timing models"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SimulationClock(BaseModel):
    """Global simulation clock tracking ticks"""

    current_tick: int = Field(default=0, ge=0)
    total_ticks: int = Field(default=0, ge=0)

    def advance(self) -> "SimulationTick":
        """Advance to next tick and return a SimulationTick object"""
        self.current_tick += 1
        self.total_ticks += 1
        return SimulationTick(tick=self.current_tick)

    def reset(self) -> None:
        """Reset clock to tick 0"""
        self.current_tick = 0
        self.total_ticks = 0


class SimulationTick(BaseModel):
    """Represents a single simulation tick"""

    tick: int = Field(..., ge=0)
    timestamp: Optional[str] = None  # ISO 8601 format if desired

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"tick": 1, "timestamp": "2026-09-11T10:00:00Z"}
        }
    )
