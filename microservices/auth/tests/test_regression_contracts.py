from __future__ import annotations

from auth.api.identity import (
    ActivationComplete,
    ActivationStart,
    ChallengeStart,
    ChallengeVerify,
    LogoutRequest,
    RefreshRequest,
)
from auth.main import create_app


def test_backward_compatible_identity_routes_remain_registered() -> None:
    paths = {route.path for route in create_app().routes if hasattr(route, "path")}
    expected = {
        "/auth/register/{channel}/start",
        "/auth/register/{channel}/verify",
        "/auth/email/activation/start",
        "/auth/email/activation/complete",
        "/auth/refresh",
        "/auth/logout",
        "/auth/me",
        "/auth/oauth/{provider}/start",
        "/auth/oauth/{provider}/callback",
        "/auth/login",
        "/auth/link",
        "/auth/link/{provider}",
    }
    assert expected <= paths


def test_legacy_portal_request_shapes_still_validate() -> None:
    assert ChallengeStart(destination="user@example.com").purpose == "registration"
    assert ChallengeVerify(destination="user@example.com", code="123456").account_type == "user"
    assert ActivationStart(email="user@example.com").account_type == "user"
    assert ActivationComplete(token="t" * 32).token == "t" * 32
    assert RefreshRequest(refresh_token="r" * 32).refresh_token == "r" * 32
    assert LogoutRequest().refresh_token is None
