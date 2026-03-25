from pydantic import BaseModel, Field


class FatigueScore(BaseModel):
    local_muscular: float = Field(..., ge=0, le=100)
    cns_load: float = Field(..., ge=0, le=100)
    metabolic_cost: float = Field(..., ge=0, le=100)
    recovery_hours: float = Field(..., ge=0)
    affected_muscles: list[str] = Field(default_factory=list)
