"""SQLAlchemy ORM models for the Billing Service.

Author: Farruh
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UsageRecordORM(Base):
    """Persisted usage record for every API call."""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    api_key_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    markup_usd: Mapped[float] = mapped_column(Float, default=0.0)
    billed_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    cache_hit: Mapped[bool] = mapped_column(Boolean, default=False)
    cached_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_discount_usd: Mapped[float] = mapped_column(Float, default=0.0)

    # Phase 4 — Task 4.3: A/B testing
    experiment_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    experiment_variant: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Phase 4 — Task 4.4: Structured output validation
    schema_validation_passed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    validation_retry_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
