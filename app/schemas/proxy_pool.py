from datetime import datetime
from pydantic import BaseModel, field_validator

from app.models.proxy_pool import ProxyProtocol


class ProxyCreate(BaseModel):
    host: str
    port: int
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    username: str | None = None
    password: str | None = None

    @field_validator("port")
    @classmethod
    def port_valid(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError("port must be between 1 and 65535")
        return v

    @field_validator("host")
    @classmethod
    def host_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("host cannot be empty")
        return v.strip()


class ProxyUpdate(BaseModel):
    is_active: bool | None = None
    username: str | None = None
    password: str | None = None


class ProxyResponse(BaseModel):
    id: int
    host: str
    port: int
    protocol: ProxyProtocol
    is_active: bool
    success_rate: float
    response_time_ms: int
    last_used_at: datetime | None
    last_checked_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
