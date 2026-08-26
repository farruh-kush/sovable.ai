# Auth and Identity Service

The Auth Service owns first-party identity records, activation links, password authentication, OAuth identity links, refresh sessions, and API-key metadata. It owns the `auth_db` PostgreSQL database and communicates with the Gateway only over HTTP REST. It never returns password hashes, DirectMail credentials, raw API-key values except at creation time, activation tokens, or refresh-token values in logs.

## HTTP contract

The existing portal routes remain available and keep their request and response field names:

| Route | Purpose |
| --- | --- |
| `POST /auth/register/{channel}/start` | Start legacy email or phone OTP registration/login challenge. |
| `POST /auth/register/{channel}/verify` | Consume one OTP and issue a first-party session. |
| `POST /auth/email/activation/start` | Create and email a hashed, single-use activation link. |
| `POST /auth/email/activation/complete` | Consume the activation link and issue a session. |
| `POST /auth/login` | Password login with enumeration-resistant failures. |
| `POST /auth/refresh` | Rotate a refresh token and revoke the old session token. |
| `POST /auth/logout` | Idempotently revoke a refresh token. |
| `GET /auth/me` | Return the authenticated account’s safe identity payload. |
| `POST /auth/link` | Link an OAuth/provider subject to the authenticated account. |
| `DELETE /auth/link/{provider}` | Remove a linked provider when another sign-in method remains. |
| `PATCH /auth/users/{user_id}/role` | Role management; only platform controllers can grant `platform_controller`. |
| `POST/GET/DELETE /v1/keys` | Role-guarded API-key creation, listing, and revocation. |
| `POST /internal/validate-key` | Gateway-compatible API-key validation; only the hash is queried and returned data is a shared principal. |

Roles are `user`, `org_admin`, `agent_creator`, and `platform_controller`. An organization administrator is scoped to their own account and cannot grant platform-controller access or manage another account’s API key. Platform-controller access is never granted by a client-selected `admin` or `creator` registration field.

## Environment variables

The service loads settings from environment variables. Non-secret values may be supplied through a ConfigMap. The variables in the secret column must be sourced from Kubernetes Secrets or an equivalent secret manager. In a multi-replica deployment, set `RATE_LIMIT_BACKEND=redis` and provide `REDIS_URL`; the default in-memory limiter is intended only for local development and tests.

| Variable | Secret | Default / example | Notes |
| --- | ---: | --- | --- |
| `APP_ENV` | No | `development` | Set `production` for production startup validation. |
| `LOG_LEVEL` | No | `INFO` | Structured JSON logs are emitted by `structlog`. |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://postgres:postgres@postgres:5432/auth_db` | Auth database only. |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Shared rate-limit backend when `RATE_LIMIT_BACKEND=redis`. |
| `RATE_LIMIT_BACKEND` | No | `memory` | Use `redis` in multi-replica production; memory is for local/test use. |
| `SECRET_KEY` | Yes | No production default | JWT signing key and server-side hash pepper. Production refuses the placeholder. |
| `PUBLIC_BASE_URL` | No | `https://api.sovable.ai` | OAuth callback base. |
| `FRONTEND_BASE_URL` | No | `https://sovable.ai` | Activation and OAuth redirect base. |
| `ACCESS_TOKEN_TTL_SECONDS` | No | `900` | Short-lived access-token lifetime. |
| `REFRESH_TOKEN_TTL_DAYS` | No | `30` | Refresh-session lifetime. |
| `ACTIVATION_LINK_TTL_SECONDS` | No | `3600` | Single-use activation-token lifetime. |
| `ACTIVATION_EMAIL_PROVIDER` | No | `directmail` | Delivery provider identifier returned in the accepted response. |
| `DIRECTMAIL_ACCESS_KEY_ID` | Yes | Empty | Alibaba DirectMail credential. |
| `DIRECTMAIL_ACCESS_KEY_SECRET` | Yes | Empty | Alibaba DirectMail credential. |
| `DIRECTMAIL_ACCOUNT_NAME` | No | Empty | Verified DirectMail sender account. |
| `DIRECTMAIL_ENDPOINT` | No | `dm.ap-southeast-1.aliyuncs.com` | Alibaba regional endpoint. |
| `DIRECTMAIL_FROM_ALIAS` | No | `Solvable AI` | Truncated to the provider limit by the adapter. |
| `DIRECTMAIL_TIMEOUT_SECONDS` | No | `30` | Connect, read, and async delivery timeout boundary. |
| `OTP_DELIVERY_MODE` | No | `disabled` | Preserves the legacy OTP response contract. |
| `ALLOW_DEV_OTP` | No | `false` | Must remain false in production. |
| `OTP_TTL_SECONDS` | No | `600` | OTP lifetime. |
| `OTP_MAX_ATTEMPTS` | No | `5` | Maximum failed attempts per challenge. |
| `LOGIN_RATE_LIMIT` | No | `10` | Auth issuance attempts per identifier/window. |
| `ACTIVATION_RATE_LIMIT` | No | `5` | Activation issuance attempts per identifier/window. |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Rate-limit window. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | Secret for secret | Empty | Google OAuth configuration. |
| `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`, `APPLE_REDIRECT_URI` | Secret for private key | Empty | Apple OAuth configuration. |
| `OIDC_PROVIDERS_JSON` | Possibly | `{}` | JSON configuration for additional OIDC providers. |

Example Kubernetes wiring:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: auth-secrets
        key: database-url
  - name: SECRET_KEY
    valueFrom:
      secretKeyRef:
        name: auth-secrets
        key: secret-key
  - name: DIRECTMAIL_ACCESS_KEY_ID
    valueFrom:
      secretKeyRef:
        name: auth-secrets
        key: directmail-access-key-id
  - name: DIRECTMAIL_ACCESS_KEY_SECRET
    valueFrom:
      secretKeyRef:
        name: auth-secrets
        key: directmail-access-key-secret
```

Do not put these values in Docker build arguments, image layers, request bodies used for debugging, or structured log fields.

## Migrations

Schema changes are deterministic and run through Alembic. The container entrypoint executes `alembic upgrade head` before Uvicorn starts. The current head is `f6a1b2c3d4e5_password_auth`, which adds nullable password-hash columns to `user_accounts` and `email_activation_tokens`; nullable columns preserve existing OTP/OAuth accounts.

From the repository root:

```bash
cd microservices/auth
DATABASE_URL='postgresql+asyncpg://.../auth_db' alembic upgrade head
DATABASE_URL='postgresql+asyncpg://.../auth_db' alembic current
DATABASE_URL='postgresql+asyncpg://.../auth_db' alembic history
```

Never use `Base.metadata.create_all()` in application startup. To add schema, update the ORM model and create a revision with `alembic revision --autogenerate -m 'describe change'`; review the generated SQL and make the revision deterministic before committing it.

## Local validation and debugging

Use the service-local virtual environment and explicit source paths when running from a checkout:

```bash
PYTHONPATH=backend/shared/src:microservices/auth/src \
  .venv/bin/python -m pytest -q microservices/auth/tests

PYTHONPATH=backend/shared/src:microservices/auth/src \
  .venv/bin/python -m compileall -q backend/shared/src/ai_routing_shared microservices/auth/src

docker build -f microservices/auth/Dockerfile -t solvable-auth:local .
docker compose up -d postgres auth gateway
curl -fsS http://localhost:8001/health
```

For a failed activation delivery, inspect only request IDs, status codes, and the normalized `email_delivery_failed` boundary. Do not print exception chains, settings objects, activation URLs, or request bodies. For a session issue, compare the session row’s `revoked_at` and `expires_at` fields against UTC time; refresh tokens are stored only as hashes.

## Rollback

Application rollback is safe only when the target image understands the existing schema. First stop new traffic or scale the Auth Service deployment to zero, record the deployed image digest and current Alembic revision, then deploy the previous known-good image. Because the password columns are nullable, rolling back the application without downgrading the database is the preferred recovery path.

Only downgrade the migration when the previous application cannot tolerate the extra columns and a database backup has been verified:

```bash
cd microservices/auth
DATABASE_URL='postgresql+asyncpg://.../auth_db' alembic downgrade e5f9a2b6c7d8
```

A migration downgrade permanently removes password hashes from `user_accounts` and pending activation records. It invalidates password login for accounts created through the password flow and must therefore be treated as a destructive operation requiring an approved backup and change record. Re-run `alembic upgrade head` before restoring the new image.

## Canonical repository integration notes

The `shared/` directory in the canonical `sovable-auth` repository is a buildable snapshot of [`sovable-shared-contracts`](https://github.com/farruh-kush/sovable-shared-contracts); its source commit is recorded in `SHARED_SNAPSHOT`. The public backend boundary is the Gateway on `api.sovable.ai:8000`. Auth, Router, Provider, and Billing remain ClusterIP-only in Kubernetes, and the platform release repository validates this service together with the other pinned components.
