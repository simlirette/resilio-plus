from pydantic import BaseModel


class ConnectorStatus(BaseModel):
    provider: str           # "strava" | "hevy"
    connected: bool
    expires_at: int | None  # epoch seconds (int); None for API key providers


class HevyConnectRequest(BaseModel):
    api_key: str


class ConnectorListResponse(BaseModel):
    connectors: list[ConnectorStatus]
