"""API key and access control domain models.

Author: Farruh
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ApiKeyTier(str, Enum):
    """User tier determines default rate limits and quota."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ApiKey(BaseModel):
    """Validated API key principal.

    Populated by the Auth Service and forwarded to the Gateway for
    enforcement of rate limits, budget caps, and model whitelists.
    """

    id: str
    user_id: str
    tier: ApiKeyTier = ApiKeyTier.FREE
    requests_per_minute: int = 60
    requests_per_day: int = 2000

    # Phase 1 — Task 1.2: Monthly budget enforcement
    monthly_budget_usd: Optional[float] = None

    # Phase 1 — Task 1.3: Model whitelist enforcement
    allowed_models: Optional[List[str]] = None

    is_active: bool = True
