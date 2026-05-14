import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProxyProtocol(str, enum.Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


class ProxyPool(Base):
    __tablename__ = "proxy_pool"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    protocol: Mapped[ProxyProtocol] = mapped_column(Enum(ProxyProtocol), default=ProxyProtocol.HTTP)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    success_rate: Mapped[float] = mapped_column(Float, default=1.0)
    response_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def get_url(self) -> str:
        if self.username and self.password:
            return f"{self.protocol.value}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol.value}://{self.host}:{self.port}"
