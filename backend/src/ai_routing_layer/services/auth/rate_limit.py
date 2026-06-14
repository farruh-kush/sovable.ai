from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from ai_routing_layer.auth.service import Principal


class RateLimiter:
    def __init__(self) -> None:
        self._minute_windows: dict[str, deque[datetime]] = defaultdict(deque)
        self._day_windows: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, principal: Principal) -> None:
        now = datetime.now(timezone.utc)
        minute_cutoff = now - timedelta(minutes=1)
        day_cutoff = now - timedelta(days=1)

        minute_entries = self._minute_windows[principal.api_key_id]
        while minute_entries and minute_entries[0] < minute_cutoff:
            minute_entries.popleft()

        day_entries = self._day_windows[principal.api_key_id]
        while day_entries and day_entries[0] < day_cutoff:
            day_entries.popleft()

        if len(minute_entries) >= principal.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Per-minute rate limit exceeded",
            )

        if len(day_entries) >= principal.requests_per_day:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Per-day rate limit exceeded",
            )

        minute_entries.append(now)
        day_entries.append(now)
