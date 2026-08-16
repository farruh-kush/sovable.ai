"""SQLAlchemy ORM models for the Auth Service.

Author: Farruh
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ApiKeyRecord(Base):
    """Persisted API key record.

    The raw key is never stored — only its SHA-256 fingerprint.
    """

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tier: Mapped[str] = mapped_column(String(32), default="free")
    requests_per_minute: Mapped[int] = mapped_column(Integer, default=60)
    requests_per_day: Mapped[int] = mapped_column(Integer, default=2000)

    # Phase 1 — Task 1.2: Monthly budget enforcement
    monthly_budget_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Phase 1 — Task 1.3: Model whitelist enforcement
    allowed_models: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
