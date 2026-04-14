from pydantic import BaseModel


class SyncSummary(BaseModel):
    synced: int
    skipped: int  # activities with unrecognized sport_type
    sport_breakdown: dict[str, int]  # {"running": N, "biking": N, "swimming": N}
