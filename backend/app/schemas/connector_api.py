from pydantic import BaseModel, Field


class ConnectorStatus(BaseModel):
    provider: str           # "strava" | "hevy"
    connected: bool
    expires_at: int | None  # epoch seconds (int); None for API key providers


class HevyConnectRequest(BaseModel):
    api_key: str = Field(..., min_length=1)


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
