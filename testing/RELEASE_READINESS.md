# Solvable AI Release Readiness

**Owner:** Testing workstream
**Execution policy:** Read-only against production; external providers are mocked in CI.
**Fixture:** `testing/fixtures/platform_fixture.json`
**Runner:** `./testing/scripts/run_tests.sh` or `python testing/scripts/release_gate.py --mode ci`

## Release decision

A production release is **PASS** only when the CI release-gate job is green, all required service-local suites are green, the ACK overlay renders successfully, no security or isolation check fails, the staging smoke suite is green for the release candidate, and the rollback review has been recorded. A skipped optional integration is acceptable only when the release checklist records the reason, owner, and follow-up date. Any failure involving authentication, privacy masking, quota enforcement, usage accounting, cross-service isolation, secret exposure, deployment health, or rollback is an automatic **NO-GO**.

The runner does not apply Kubernetes manifests, call production hosts, or execute a rollback during ordinary CI. The optional staging rollback procedure requires `PLATFORM_TARGET_ENV=staging`, rejects production namespaces, and must be executed by an authorized release operator during a controlled window.

## Test matrix

| Area | Required scenarios | Automated location | Gate |
|---|---|---|---|
| Shared contracts | Chat request/response, SSE chunks, embeddings, usage records, error taxonomy | `test_contracts.py`, `test_release_surface.py` | Required |
| Gateway | Health, API-key boundary, model whitelist, rate limit, monthly budget, chat, streaming, embeddings, cache headers, generation headers | Service tests plus `test_staging_smoke.py` | Required |
| Auth | Registration start/verify, activation start/complete, login/session refresh/logout, API-key lifecycle, role boundaries, rate limits, invalid credentials | `microservices/auth/tests/` plus staging smoke | Required |
| Router/aggregator | Static and dynamic policy selection, provider order, cost/latency strategy, data-collection deny policy, fallback, timeout, usage emission | `microservices/router/tests/`, provider boundary tests | Required |
| Provider | Adapter normalization, mock chat/streaming/embeddings, retryable versus non-retryable errors, circuit behavior, capability boundary, endpoint safety | `microservices/provider/tests/`, `testing/mocks/provider_mock.py` | Required |
| Billing | Usage ingestion, pricing/markup, monthly spend, generation lookup, quota evidence, duplicate/failed event triage | `microservices/billing/tests/` and integration environment | Required |
| Privacy | Email, phone, card and UZ-ID masking; request-local restoration; preview does not return originals; masked logs/evidence | `test_security_isolation.py` | Required |
| Frontend | UZ/RU/EN portal surfaces, auth/activation, dashboard keys/playground, App Store, creator register/login, admin routes | `test_release_surface.py`, frontend typecheck/build, staging smoke | Required |
| Admin/user boundary | Admin and creator route inventory, unauthorized API behavior, no cross-tenant identifiers in responses | Service security tests and staging identity matrix | Required |
| Deployment | ACK/Kustomize render, six deployments/services, health endpoints, readiness, ingress/TLS policy | `release_gate.py --mode ack`, CI render step | Required |
| Performance | Bounded concurrent workload, p50/p95/max latency and error rate | `testing/scripts/load_smoke.py` | Required for release profile |
| Resilience/recovery | Provider timeout, retry budget, fallback chain, circuit open, billing outage isolation, restart/readiness, rollback | Provider/router tests, `rollback_verify.py` | Required |
| Optional integrations | Alibaba Model Studio staging call and DirectMail staging delivery | Explicit operator-run checks | Conditional |

## Deterministic execution

The default command runs service-local tests and non-staging platform checks with `testing/pytest.ini`. It writes JUnit output to `testing/evidence/platform-junit.xml`. The CI workflow installs bounded major-version dependencies, sets `PLATFORM_TARGET_ENV=ci`, uses the deterministic fixture, and uploads only the evidence directory. No real API key is required; provider calls use the local mock contract.

```bash
./testing/scripts/run_tests.sh
python testing/scripts/release_gate.py --mode ci
python testing/scripts/load_smoke.py --url http://127.0.0.1:8000/health --requests 20
```

The staging path is opt-in and refuses known production hosts. Configure `PLATFORM_TARGET_ENV=staging`, `GATEWAY_BASE_URL`, and any required service or dashboard URLs before running `python testing/scripts/release_gate.py --mode staging`. Mutating activation and billing checks additionally require `RUN_MUTATING_STAGING_SMOKE=1` and must use a disposable staging identity.

## Performance thresholds

The default smoke threshold is **p95 ≤ 1,000 ms**, **error rate ≤ 1%**, and a bounded run of **20 requests**. Release operators should replace these defaults with the approved service-level objective for the candidate using `LOAD_P95_MS`, `LOAD_MAX_ERROR_RATE`, and `LOAD_REQUESTS`. A streaming test must receive `text/event-stream`, a terminal `[DONE]` event, and no upstream secret or unmasked sensitive value. Load runs must be bounded to 1,000 requests or fewer and must not target production.

| Signal | Default gate | Failure action |
|---|---:|---|
| Health HTTP status | 200 | Stop and triage deployment/readiness |
| Chat/embedding 5xx rate | ≤ 1% | Investigate provider, router, or quota path |
| Health p95 latency | ≤ 1,000 ms | Compare against baseline; block if regression is unexplained |
| SSE completion | `[DONE]` present | Block streaming release |
| Privacy masking | Original value absent at provider boundary | Immediate NO-GO |
| Billing emission | Client response survives billing outage; event is observable | Block if request fails or accounting disappears |
| Rollback | Staging deployment returns healthy after undo | Block production release |

## Evidence and masking

Evidence must contain test names, status, duration, HTTP status, service name, and a short sanitized output tail. It must not contain bearer tokens, API keys, private keys, activation tokens, passwords, email contents, phone numbers, card numbers, provider prompts, or full response bodies. The release runner masks common authorization and key patterns before writing report output. Reviewers must delete accidental sensitive artifacts and rerun the gate; do not paste secrets into CI comments.

## Failure triage

Start with the first failing check, its request ID, and the service boundary named in the error. If the failure is authentication, verify the auth service response contract, expiry handling, and API-key header parsing without printing the raw key. If the failure is routing or provider related, reproduce with `MOCK_PROVIDER_MODE=error` or `timeout`, inspect retry and circuit metrics, and confirm fallback policy. If the failure is billing, compare the generation ID in the normalized response with the usage event and billing record; billing unavailability must be visible but must not corrupt the client response. If the failure is privacy or isolation, stop the release immediately and preserve only masked evidence. If the failure is deployment, render the exact candidate overlay, check pod readiness and ingress, and use the controlled rollback procedure.

A failure is not resolved by rerunning alone. The owner must identify whether it is a product defect, environment defect, fixture defect, or flaky test, attach sanitized evidence, and record the corrective commit or an approved waiver. Waivers cannot cover security, data isolation, quota leakage, accounting loss, or rollback failures.

## ACK smoke and rollback

Render-only ACK validation is safe in CI:

```bash
python testing/scripts/release_gate.py --mode ack
```

For an already deployed non-production namespace, set `ACK_HEALTH_URLS` to comma-separated `name=url` health endpoints. The smoke utility rejects `api.sovable.ai`, `sovable.ai`, and `www.sovable.ai`. The normal release gate never calls `kubectl apply`, `kubectl set image`, `kubectl rollout restart`, or `kubectl rollout undo`.

Review rollback readiness without mutation:

```bash
python testing/scripts/rollback_verify.py --namespace ai-routing-staging --deployment gateway
```

A controlled staging rollback may be applied only after the operator has confirmed staging target and namespace:

```bash
PLATFORM_TARGET_ENV=staging \
python testing/scripts/rollback_verify.py \
  --namespace ai-routing-staging --deployment gateway --apply-staging
```

Verify each service that changed, not only the gateway. Record the pre-rollback candidate, the restored revision, rollout status, health matrix, and post-rollback chat/embedding smoke results.

## Production checklist

| Check | Owner | Evidence | Status |
|---|---|---|---|
| CI release-gate workflow green | Release engineer | GitHub Actions run URL | [ ] |
| Service-local suites green | Service owners | JUnit artifact | [ ] |
| Shared contracts unchanged or reviewed | Contracts owner | Diff/review link | [ ] |
| Auth, API keys, sessions, activation tested | Auth owner | Sanitized report | [ ] |
| Router policies, fallback, timeouts tested | Router/provider owners | Sanitized report | [ ] |
| Billing usage/cost/quota reconciliation complete | Billing owner | Reconciliation artifact | [ ] |
| Privacy masking and source scan green | Security owner | Security test artifact | [ ] |
| UZ/RU/EN, App Store, creator, admin boundaries green | Frontend owner | Build and staging smoke | [ ] |
| ACK overlay render and health matrix green | Platform owner | Render/smoke artifact | [ ] |
| Approved performance thresholds met | SRE owner | Load report | [ ] |
| Model Studio and DirectMail staging checks recorded if enabled | Integration owners | Sanitized check log | [ ] |
| Staging rollback verified | Release engineer | Rollback report | [ ] |
| No production mutation during validation | Release engineer | Runner report | [ ] |
| Final PASS/NO-GO decision recorded | Release owner | Change record | [ ] |
