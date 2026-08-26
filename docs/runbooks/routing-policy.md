# Routing Policy and Model Catalog Runbook

The governed source of truth is `ai/config/routing.yaml`. The legacy `config/routing.yaml` and Kubernetes `k8s/base/routing.yaml` paths point to that file for compatibility. Credentials are never stored in the catalog; provider adapters read the environment variables named by `api_key_env` and endpoint variables named by `base_url_env`.

## Policy evaluation contract

Every decision is deterministic for the tuple `(catalog_version, policy_version, tenant_id, correlation_id, requested_model, request constraints)`. Hard constraints run before preferences: deny-list, tenant compliance, region, capability/modality, quota and cost cap, provider health, explicit provider order, experiment assignment, strategy scoring, and static fallback order. Ties are resolved by configured provider order and then model identifier.

The router returns a decision identifier and correlation ID through the typed route-decision contract. Reasons contain policy version, strategy, candidate order, rejected-provider reasons, and experiment assignment when applicable. Raw prompts, response bodies, API keys, cookies, and reversible PII token maps are not part of the audit contract.

## Debugging a route

Start with the client-visible `X-Request-Id` or `X-Correlation-Id`, then query `GET /route/routing/decisions/{request_id}`. Compare `policy_version`, `catalog_version`, `checksum`, selected provider, candidate order, and rejected reasons with `GET /route/routing/summary` and `GET /route/health`. A `circuit_open` or `provider_error_rate_high` rejection indicates a health gate; `region_not_allowed`, `gdpr_required`, `zero_data_retention_required`, and `self_hosted_required` indicate hard compliance gates.

If a request fails after all candidates are exhausted, inspect provider service health and adapter logs using the same correlation ID. Retry-safe operations may retry transient failures, but streaming requests must not replay after the first byte. Billing attribution failures must not change the already-returned client response.

## Safe rollout and reload

1. Edit `ai/config/routing.yaml` in a reviewed change. Increment `catalog_version` for catalog metadata changes and `policy_version` for routing-policy changes.
2. Run `PYTHONPATH=shared/src:services/router/src python scripts/validate_routing_catalog.py`.
3. Run the service and shared contract suites. Run `python scripts/run_routing_evaluation.py` and retain the JSON report with its catalog checksum.
4. Confirm no secret values, prompts, customer data, or credentials appear in the diff or generated report.
5. Deploy the immutable image/configuration bundle. The router validates before an atomic snapshot swap. If parsing fails, the last valid snapshot remains active and a reload audit event is emitted.
6. Start with a restricted tier or paused experiment. Promote only when the configured evaluation gate is met: at least 200 synthetic/evaluation requests, availability at least 99.5%, zero masking leakage, fallback rate at most 20%, and no material quality, latency, or cost regression.

Rollback by restoring the last known-good catalog and policy versions or deploying the previous immutable image. Confirm the checksum from `GET /route/routing/summary`, then run a non-sensitive authenticated smoke request. Do not place emergency secrets or raw customer prompts in tickets.

## Emergency deny-list and deprecation

To stop a model immediately, add its identifier to `deny_list`, increment `policy_version`, validate, and deploy/reload. The deny-list has precedence over all preferences and experiments. Remove the identifier only after provider health and a reproducible evaluation report pass the promotion gate.

To deprecate a model, set `deprecation.status: deprecated`, provide `sunset_at` and a reviewed `replacement`, and remove it from new experiment candidates. Keep the fallback chain explicit until the sunset date; then set the route to the replacement and retain the old entry for auditability.

## Privacy and tenant isolation

Masking is mandatory before provider calls. The masking session is request-local and restores only the response associated with that request. Provider policy cannot disable masking. Do not log raw values or token maps. Cache keys and usage events must include the validated tenant/API-key identity; never reuse a masked response or reversible token mapping across tenants or requests.
