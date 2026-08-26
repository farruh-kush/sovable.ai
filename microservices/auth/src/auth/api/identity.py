"""Public identity, registration, account-linking, and session endpoints."""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any, Literal
from urllib.parse import urlencode

import httpx
import jwt
from ai_routing_shared.exceptions import (
    AuthenticationError,
    AuthorisationError,
    EmailDeliveryError,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import AuthSettings, get_settings
from ..db.database import get_session
from ..db.models import (
    AuthSession,
    EmailActivationToken,
    UserAccount,
    UserIdentity,
    VerificationChallenge,
)
from ..security.dependencies import current_user, public_user_payload, require_roles
from ..security.email import send_activation_email
from ..security.identity import (
    ACCOUNT_TYPE_TO_ROLE,
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_value,
    normalize_email,
    normalize_phone,
    now_utc,
    provider_config,
    random_code,
    secret_value,
    verify_password,
)
from ..security.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Identity"])


class ChallengeStart(BaseModel):
    destination: str = Field(min_length=3, max_length=320)
    purpose: Literal["registration", "login", "link", "recovery"] = "registration"
    account_type: Literal["user", "admin", "creator"] = "user"


class ChallengeVerify(BaseModel):
    destination: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    purpose: Literal["registration", "login", "link", "recovery"] = "registration"
    account_type: Literal["user", "admin", "creator"] = "user"
    display_name: str | None = Field(default=None, max_length=255)


class ActivationStart(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    account_type: Literal["user", "admin", "creator"] = "user"


class ActivationComplete(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PasswordLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)
    account_type: Literal["user", "admin", "creator"] = "user"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=256)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, min_length=32, max_length=256)


class AccountLinkRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    provider_subject: str = Field(min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=320)


class RoleUpdateRequest(BaseModel):
    role: Literal["user", "org_admin", "agent_creator", "platform_controller"]


def _destination(channel: str, value: str) -> str:
    try:
        return normalize_email(value) if channel == "email" else normalize_phone(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _role_for(account_type: str) -> str:
    return ACCOUNT_TYPE_TO_ROLE.get(account_type, "user")


def _user_payload(
    user: UserAccount, settings: AuthSettings, access_token: str, refresh_token: str
) -> dict[str, Any]:
    return {
        "user": public_user_payload(user),
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": settings.access_token_ttl_seconds,
        "refresh_token": refresh_token,
    }


async def _create_session(
    session: AsyncSession, settings: AuthSettings, user: UserAccount, request: Request
) -> dict[str, Any]:
    refresh_token = create_refresh_token()
    record = AuthSession(
        id=secrets.token_hex(16),
        user_id=user.id,
        refresh_token_hash=hash_value(settings, refresh_token),
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        expires_at=now_utc() + timedelta(days=settings.refresh_token_ttl_days),
    )
    session.add(record)
    await session.commit()
    return _user_payload(user, settings, create_access_token(settings, user), refresh_token)


async def _find_or_create_identity(
    session: AsyncSession,
    provider: str,
    subject: str,
    email: str | None,
    display_name: str | None,
) -> UserAccount:
    existing_identity = await session.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == provider, UserIdentity.provider_subject == subject
        )
    )
    if existing_identity:
        user = await session.get(UserAccount, existing_identity.user_id)
        if user:
            return user
    user = None
    if email:
        user = await session.scalar(select(UserAccount).where(UserAccount.email == email))
    if user is None:
        user = UserAccount(
            id=secrets.token_hex(16),
            display_name=display_name,
            email=email,
            email_verified=bool(email),
        )
        session.add(user)
        await session.flush()
    session.add(
        UserIdentity(
            id=secrets.token_hex(16),
            user_id=user.id,
            provider=provider,
            provider_subject=subject,
            email_at_link=email,
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AuthenticationError("This identity is already linked to another account.") from exc
    return user


@router.post("/register/{channel}/start")
async def start_challenge(
    channel: str,
    body: ChallengeStart,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Start an email or phone verification challenge."""
    if channel not in {"email", "phone"}:
        raise HTTPException(status_code=404, detail="Supported channels are email and phone")
    destination = _destination(channel, body.destination)
    await limiter.check(
        f"challenge:{hash_value(settings, destination)}",
        settings.login_rate_limit,
        settings.rate_limit_window_seconds,
    )
    code = random_code()
    session.add(
        VerificationChallenge(
            id=secrets.token_hex(16),
            channel=channel,
            destination_hash=hash_value(settings, destination),
            code_hash=hash_value(settings, code),
            purpose=body.purpose,
            account_type=body.account_type,
            expires_at=now_utc() + timedelta(seconds=settings.otp_ttl_seconds),
        )
    )
    await session.commit()
    result: dict[str, Any] = {
        "status": "accepted",
        "channel": channel,
        "destination": destination,
        "delivery": settings.otp_delivery_mode,
        "expires_in": settings.otp_ttl_seconds,
    }
    if settings.allow_dev_otp and settings.app_env != "production":
        result["dev_code"] = code
    return result


@router.post("/email/activation/start")
async def start_email_activation(
    body: ActivationStart,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Create and deliver a single-use registration activation link.

    Only a hash of the token is persisted, and the raw token appears only in
    the provider request. It is never returned or logged by this service.
    """
    email = _destination("email", body.email)
    await limiter.check(
        f"activation:{hash_value(settings, email)}",
        settings.activation_rate_limit,
        settings.rate_limit_window_seconds,
    )
    existing = await session.scalar(select(UserAccount).where(UserAccount.email == email))
    if existing and existing.email_verified:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists. Sign in instead.",
        )
    password_hash = hash_password(body.password) if body.password else None
    raw_token = secrets.token_urlsafe(48)
    session.add(
        EmailActivationToken(
            id=secrets.token_hex(16),
            token_hash=hash_value(settings, raw_token),
            email=email,
            display_name=body.display_name,
            password_hash=password_hash,
            account_type=body.account_type,
            expires_at=now_utc() + timedelta(seconds=settings.activation_link_ttl_seconds),
        )
    )
    await session.commit()
    activation_url = f"{settings.frontend_base_url.rstrip('/')}/auth/activate?token={raw_token}"
    try:
        await send_activation_email(settings, email, activation_url)
    except EmailDeliveryError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=503,
            detail=(
                "Email delivery is not available. Check the configured email provider "
                "and try again."
            ),
        ) from exc
    return {
        "status": "accepted",
        "delivery": settings.activation_email_provider,
        "expires_in": settings.activation_link_ttl_seconds,
    }


@router.post("/email/activation/complete")
async def complete_email_activation(
    body: ActivationComplete,
    request: Request,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Consume an activation link exactly once and create its first session."""
    token = await session.scalar(
        select(EmailActivationToken)
        .where(
            EmailActivationToken.token_hash == hash_value(settings, body.token),
            EmailActivationToken.consumed.is_(False),
        )
        .with_for_update()
    )
    if not token or token.expires_at <= now_utc():
        raise HTTPException(
            status_code=400, detail="This activation link is invalid, expired, or already used."
        )
    user = await session.scalar(select(UserAccount).where(UserAccount.email == token.email))
    if user is not None and user.email_verified:
        token.consumed = True
        await session.commit()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists. Sign in instead."
        )
    if user is None:
        user = UserAccount(
            id=secrets.token_hex(16),
            email=token.email,
            password_hash=token.password_hash,
            email_verified=True,
            display_name=token.display_name,
            role=_role_for(token.account_type),
        )
        session.add(user)
        await session.flush()
    else:
        user.email_verified = True
        if token.password_hash:
            user.password_hash = token.password_hash
        if token.account_type in {"admin", "creator"} and user.role == "user":
            user.role = _role_for(token.account_type)
    token.consumed = True
    await session.commit()
    return await _create_session(session, settings, user, request)


@router.post("/register/{channel}/verify")
async def verify_challenge(
    channel: str,
    body: ChallengeVerify,
    request: Request,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Consume a verification code and issue a first-party session."""
    if channel not in {"email", "phone"}:
        raise HTTPException(status_code=404, detail="Supported channels are email and phone")
    destination = _destination(channel, body.destination)
    challenge = await session.scalar(
        select(VerificationChallenge)
        .where(
            VerificationChallenge.channel == channel,
            VerificationChallenge.destination_hash == hash_value(settings, destination),
            VerificationChallenge.purpose == body.purpose,
            VerificationChallenge.account_type == body.account_type,
            VerificationChallenge.consumed.is_(False),
        )
        .order_by(desc(VerificationChallenge.created_at))
        .with_for_update()
    )
    if (
        not challenge
        or challenge.expires_at <= now_utc()
        or challenge.attempts >= settings.otp_max_attempts
    ):
        raise HTTPException(status_code=400, detail="Verification code is invalid or expired")
    challenge.attempts += 1
    if not secrets.compare_digest(challenge.code_hash, hash_value(settings, body.code)):
        await session.commit()
        raise HTTPException(status_code=400, detail="Verification code is invalid or expired")
    challenge.consumed = True
    if channel == "email":
        user = await session.scalar(select(UserAccount).where(UserAccount.email == destination))
        if user is None:
            user = UserAccount(
                id=secrets.token_hex(16),
                email=destination,
                email_verified=True,
                display_name=body.display_name,
                role=_role_for(body.account_type) if body.purpose == "registration" else "user",
            )
            session.add(user)
            await session.flush()
        else:
            user.email_verified = True
    else:
        user = await session.scalar(
            select(UserAccount).where(UserAccount.phone_e164 == destination)
        )
        if user is None:
            user = UserAccount(
                id=secrets.token_hex(16),
                phone_e164=destination,
                phone_verified=True,
                display_name=body.display_name,
                role=_role_for(body.account_type) if body.purpose == "registration" else "user",
            )
            session.add(user)
            await session.flush()
        else:
            user.phone_verified = True
    if (
        body.purpose == "login"
        and body.account_type == "admin"
        and user.role not in {"org_admin", "platform_controller"}
    ):
        await session.rollback()
        raise AuthorisationError("This identity is not registered for the Admin Portal")
    if (
        body.purpose == "login"
        and body.account_type == "creator"
        and user.role not in {"agent_creator", "platform_controller"}
    ):
        await session.rollback()
        raise AuthorisationError("This identity is not registered for the Agent Creator Portal")
    session.add(
        UserIdentity(
            id=secrets.token_hex(16),
            user_id=user.id,
            provider=channel,
            provider_subject=destination,
            email_at_link=user.email,
        )
    )
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AuthenticationError(
            "This identity is already linked to another account."
        ) from exc
    return await _create_session(session, settings, user, request)


@router.post("/login")
async def login(
    body: PasswordLoginRequest,
    request: Request,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Authenticate by password with an enumeration-resistant failure message."""
    email = _destination("email", body.email)
    client_ip = request.client.host if request.client else "unknown"
    await limiter.check(
        f"login:{client_ip}:{hash_value(settings, email)}",
        settings.login_rate_limit,
        settings.rate_limit_window_seconds,
    )
    user = await session.scalar(select(UserAccount).where(UserAccount.email == email))
    valid = bool(
        user
        and user.status == "active"
        and user.email_verified
        and verify_password(body.password, user.password_hash)
    )
    if not valid:
        raise AuthenticationError("Invalid email or password")
    if body.account_type == "admin" and user.role not in {"org_admin", "platform_controller"}:
        raise AuthorisationError("This identity is not registered for the Admin Portal")
    if body.account_type == "creator" and user.role not in {"agent_creator", "platform_controller"}:
        raise AuthorisationError("This identity is not registered for the Agent Creator Portal")
    return await _create_session(session, settings, user, request)


def _oauth_state(settings: AuthSettings, provider: str) -> str:
    issued = now_utc()
    return jwt.encode(
        {
            "iss": "sovable-auth",
            "aud": "sovable-auth-state",
            "provider": provider,
            "nonce": secrets.token_urlsafe(24),
            "iat": int(issued.timestamp()),
            "exp": int((issued + timedelta(minutes=10)).timestamp()),
        },
        secret_value(settings.secret_key),
        algorithm="HS256",
    )


def _validate_oauth_state(settings: AuthSettings, state: str, provider: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            state,
            secret_value(settings.secret_key),
            algorithms=["HS256"],
            audience="sovable-auth-state",
            issuer="sovable-auth",
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc
    if payload.get("provider") != provider:
        raise HTTPException(status_code=400, detail="OAuth provider mismatch")
    return payload


@router.get("/oauth/{provider}/start")
async def oauth_start(
    provider: str, settings: AuthSettings = Depends(get_settings)
) -> RedirectResponse:
    config = provider_config(settings, provider)
    if not config.get("client_id"):
        raise HTTPException(status_code=503, detail=f"{provider} login is not configured")
    state = _oauth_state(settings, provider)
    decoded_state = jwt.decode(
        state,
        secret_value(settings.secret_key),
        algorithms=["HS256"],
        audience="sovable-auth-state",
        issuer="sovable-auth",
    )
    params = {
        "client_id": config["client_id"],
        "response_type": "code",
        "redirect_uri": config["redirect_uri"],
        "scope": config.get("scope", "openid email profile"),
        "state": state,
        "nonce": decoded_state["nonce"],
    }
    if provider == "apple":
        params["response_mode"] = "query"
    return RedirectResponse(
        f"{config['authorization_endpoint']}?{urlencode(params)}", status_code=302
    )


async def _apple_client_secret(settings: AuthSettings) -> str:
    if (
        not secret_value(settings.apple_private_key)
        or not settings.apple_team_id
        or not settings.apple_key_id
        or not settings.apple_client_id
    ):
        raise HTTPException(status_code=503, detail="Apple login is not configured")
    now = now_utc()
    return jwt.encode(
        {
            "iss": settings.apple_team_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "aud": "https://appleid.apple.com",
            "sub": settings.apple_client_id,
        },
        secret_value(settings.apple_private_key).replace("\\n", "\n"),
        algorithm="ES256",
        headers={"kid": settings.apple_key_id},
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    request: Request,
    code: str = Query(min_length=3),
    state: str = Query(min_length=10),
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    config = provider_config(settings, provider)
    state_payload = _validate_oauth_state(settings, state, provider)
    client_secret = config.get("client_secret", "")
    if provider == "apple":
        client_secret = await _apple_client_secret(settings)
    if not client_secret:
        raise HTTPException(status_code=503, detail=f"{provider} login is not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            config["token_endpoint"],
            data={
                "code": code,
                "client_id": config["client_id"],
                "client_secret": client_secret,
                "redirect_uri": config["redirect_uri"],
                "grant_type": "authorization_code",
            },
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=400, detail="Identity provider token exchange failed")
    tokens = response.json()
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Identity provider did not return an ID token")
    key = jwt.PyJWKClient(config["jwks_uri"]).get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256", "ES256"],
        audience=config["client_id"],
        issuer=config["issuer"],
        options={"require": ["iss", "sub", "aud", "exp", "iat"]},
    )
    if claims.get("nonce") and claims["nonce"] != state_payload.get("nonce"):
        raise HTTPException(status_code=400, detail="Identity provider nonce mismatch")
    email = claims.get("email")
    if email:
        email = _destination("email", email)
    user = await _find_or_create_identity(
        session, provider, claims["sub"], email, claims.get("name")
    )
    result = await _create_session(session, settings, user, request)
    fragment = urlencode(
        {
            "access_token": result["access_token"],
            "refresh_token": result["refresh_token"],
            "token_type": "Bearer",
        }
    )
    return RedirectResponse(
        f"{settings.frontend_base_url}/auth/callback#{fragment}", status_code=302
    )


@router.post("/refresh")
async def refresh(
    body: RefreshRequest,
    request: Request,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    record = await session.scalar(
        select(AuthSession)
        .where(
            AuthSession.refresh_token_hash == hash_value(settings, body.refresh_token),
            AuthSession.revoked_at.is_(None),
        )
        .with_for_update()
    )
    if not record or record.expires_at <= now_utc():
        raise AuthenticationError("Refresh token invalid or expired")
    user = await session.get(UserAccount, record.user_id)
    if not user or user.status != "active":
        raise AuthenticationError("User account is inactive")
    record.revoked_at = now_utc()
    await session.commit()
    return await _create_session(session, settings, user, request)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    settings: AuthSettings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    if body.refresh_token:
        record = await session.scalar(
            select(AuthSession).where(
                AuthSession.refresh_token_hash == hash_value(settings, body.refresh_token)
            )
        )
        if record and record.revoked_at is None:
            record.revoked_at = now_utc()
            await session.commit()
    return {"status": "signed_out"}


@router.get("/me")
async def me(user: UserAccount = Depends(current_user)) -> dict[str, Any]:
    return public_user_payload(user)


@router.post("/link")
async def link_account(
    body: AccountLinkRequest,
    user: UserAccount = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    email = _destination("email", body.email) if body.email else user.email
    if email and user.email and email != user.email:
        raise AuthorisationError("The identity email must match the authenticated account.")
    existing = await session.scalar(
        select(UserIdentity).where(
            UserIdentity.provider == body.provider,
            UserIdentity.provider_subject == body.provider_subject,
        )
    )
    if existing and existing.user_id != user.id:
        raise AuthorisationError("This identity is already linked to another account.")
    if not existing:
        session.add(
            UserIdentity(
                id=secrets.token_hex(16),
                user_id=user.id,
                provider=body.provider,
                provider_subject=body.provider_subject,
                email_at_link=email,
            )
        )
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise AuthorisationError("This identity is already linked to another account.") from exc
    return {"status": "linked", "provider": body.provider}


@router.delete("/link/{provider}")
async def unlink_account(
    provider: str,
    user: UserAccount = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    identity = await session.scalar(
        select(UserIdentity).where(
            UserIdentity.user_id == user.id, UserIdentity.provider == provider
        )
    )
    if not identity:
        raise HTTPException(status_code=404, detail="Linked identity not found")
    remaining = await session.scalar(
        select(UserIdentity).where(UserIdentity.user_id == user.id, UserIdentity.id != identity.id)
    )
    if not remaining and not user.password_hash:
        raise AuthorisationError("At least one sign-in method must remain linked.")
    await session.delete(identity)
    await session.commit()
    return {"status": "unlinked", "provider": provider}


@router.patch("/users/{user_id}/role")
async def update_role(
    user_id: str,
    body: RoleUpdateRequest,
    session: AsyncSession = Depends(get_session),
    actor: UserAccount = Depends(require_roles("platform_controller", "org_admin")),
) -> dict[str, Any]:
    target = await session.get(UserAccount, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User account not found")
    if body.role == "platform_controller" and actor.role != "platform_controller":
        raise AuthorisationError("Only a platform controller can grant platform controller access.")
    if actor.role == "org_admin" and target.role not in {"user", "agent_creator", "org_admin"}:
        raise AuthorisationError("Organization administrators cannot manage this account.")
    target.role = body.role
    await session.commit()
    return {"user": public_user_payload(target)}
