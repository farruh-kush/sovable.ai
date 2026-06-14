from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse, StreamingResponse
from prometheus_client import generate_latest
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Form
import secrets

from ai_routing_layer.api.dependencies import get_container
from ai_routing_layer.app_state import AppContainer
from ai_routing_layer.auth.service import Principal, require_principal
from ai_routing_layer.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
)

router = APIRouter()


# Simple UI routes for registration and obtaining API keys
@router.get("/signup", response_class=HTMLResponse)
async def signup_page():
    html = """
        <html>
            <head><title>AI Routing Layer - Sign Up</title></head>
            <body>
                <h1>Sign up for an API key</h1>
                <p>Register using a public account (Google, Apple) or email.</p>
                <div>
                    <a href="/auth/oauth?provider=google">Sign up with Google (mock)</a>
                </div>
                <div>
                    <a href="/auth/oauth?provider=apple">Sign up with Apple (mock)</a>
                </div>
                <hr />
                <form action="/signup/email" method="post">
                    <label>Name: <input name="name" /></label><br />
                    <label>Email: <input name="email" type="email" /></label><br />
                    <button type="submit">Register with email</button>
                </form>
            </body>
        </html>
        """
    return HTMLResponse(content=html)


@router.post("/signup/email", response_class=HTMLResponse)
async def signup_email(name: str = Form(...), email: str = Form(...)):
    # Generate API key and register with in-memory ApiKeyService
    from ai_routing_layer.auth.service import ApiKeyServiceHolder, Principal

    raw_key = secrets.token_urlsafe(32)
    principal = Principal(
        api_key_id=f"key_{secrets.token_hex(8)}",
        user_id=email,
        requests_per_minute=60,
        requests_per_day=2000,
        daily_quota_usd=20.0,
    )
    ApiKeyServiceHolder.service.register_key(raw_key=raw_key, principal=principal)
    html = f"<html><body><h1>Registered</h1><p>Your API key:</p><pre>{raw_key}</pre><p>Use it as: Authorization: Bearer &lt;key&gt;</p></body></html>"
    return HTMLResponse(content=html)


@router.get("/auth/oauth")
async def oauth_start(provider: str = "google"):
    # For the starter app we provide a mock OAuth redirect flow. In production,
    # replace with real OAuth2 client integration (Authlib or similar) and
    # handle provider client IDs/secrets.
    # The mock flow redirects to /auth/callback with a simulated user id.
    mock_user = f"{provider}_user_{secrets.token_hex(6)}"
    return RedirectResponse(url=f"/auth/callback?provider={provider}&mock_user={mock_user}")


@router.get("/auth/callback", response_class=HTMLResponse)
async def oauth_callback(provider: str, mock_user: str | None = None):
    # Simulate successful OAuth sign-in and issue API key
    from ai_routing_layer.auth.service import ApiKeyServiceHolder, Principal

    user_id = mock_user or f"{provider}_user"
    raw_key = secrets.token_urlsafe(32)
    principal = Principal(
        api_key_id=f"key_{secrets.token_hex(8)}",
        user_id=user_id,
        requests_per_minute=120,
        requests_per_day=5000,
        daily_quota_usd=50.0,
    )
    ApiKeyServiceHolder.service.register_key(raw_key=raw_key, principal=principal)
    html = f"<html><body><h1>{provider.title()} Sign-up Complete</h1><p>User: {user_id}</p><p>Your API key:</p><pre>{raw_key}</pre><p>Use it as: Authorization: Bearer &lt;key&gt;</p></body></html>"
    return HTMLResponse(content=html)


@router.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    request: ChatCompletionRequest,
    principal: Principal = Depends(require_principal),
    container: AppContainer = Depends(get_container),
):
    container.rate_limiter.check(principal)
    if request.stream:
        stream = container.routing_service.stream_chat_completion(request, principal)
        return StreamingResponse(stream, media_type="text/event-stream")
    return await container.routing_service.create_chat_completion(request, principal)


@router.post("/v1/embeddings", response_model=EmbeddingResponse)
async def embeddings(
    request: EmbeddingRequest,
    principal: Principal = Depends(require_principal),
    container: AppContainer = Depends(get_container),
):
    container.rate_limiter.check(principal)
    return await container.routing_service.create_embedding(request, principal)


@router.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"))


@router.get("/health")
async def health(container: AppContainer = Depends(get_container)):
    return {
        "status": "ok",
        "providers": {
            provider.name: {
                "available": provider.health.available(),
                "error_count": provider.health.error_count,
            }
            for provider in container.provider_registry.all()
        },
    }
