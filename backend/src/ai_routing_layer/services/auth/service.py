from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Optional

from fastapi import Header, HTTPException, status


@dataclass
class Principal:
    api_key_id: str
    user_id: str
    requests_per_minute: int
    requests_per_day: int
    daily_quota_usd: float


class ApiKeyService:
    def __init__(self) -> None:
        self._keys: dict[str, Principal] = {}
        self.register_key(
            raw_key="dev-default-key",
            principal=Principal(
                api_key_id="key_dev_default",
                user_id="user_dev",
                requests_per_minute=120,
                requests_per_day=5000,
                daily_quota_usd=50.0,
            ),
        )

    @staticmethod
    def fingerprint(raw_key: str) -> str:
        return sha256(raw_key.encode("utf-8")).hexdigest()

    def register_key(self, raw_key: str, principal: Principal) -> None:
        self._keys[self.fingerprint(raw_key)] = principal

    def authenticate(self, raw_key: Optional[str]) -> Principal:
        if not raw_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing API key",
            )
        principal = self._keys.get(self.fingerprint(raw_key))
        if principal is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return principal


async def require_principal(
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None),
) -> Principal:
    service = ApiKeyServiceHolder.service
    raw_key = x_api_key
    if authorization and authorization.lower().startswith("bearer "):
        raw_key = authorization[7:]
    return service.authenticate(raw_key)


class ApiKeyServiceHolder:
    service = ApiKeyService()
