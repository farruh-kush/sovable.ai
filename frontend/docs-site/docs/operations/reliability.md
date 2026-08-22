---
title: Reliability and operations
sidebar_label: Reliability
---

# Reliability and operations

Solvable is operated as independent services behind Kubernetes. The gateway is the public API boundary. Router, provider, auth, billing, and dashboard services have separate deployment and health signals.

## Incident evidence

When investigating an issue, preserve the request ID, route decision, provider attempt, status code, latency, retry count, and sanitized error. Do not copy authorization headers, provider keys, or raw prompt content into tickets or chat.

## Provider failure

Platform Admin may disable a provider when health checks, error rates, latency, policy, or a security event require it. The router should remove the provider from eligible candidates, preserve a decision reason, and use the configured fallback chain where policy allows. Re-enable only after a health check and incident note.

## API versioning

The public API is versioned by path, beginning with `/v1`. Backward-compatible fields may be added. Breaking schema changes require a new version, migration guidance, and a deprecation period. Generated OpenAPI reference pages are rebuilt from the live gateway contract during documentation CI.

## Support checklist

When reporting a problem, include the public route, UTC time, request ID, organization ID if safe, client type, expected result, actual result, and whether the issue is reproducible. Never include keys or sensitive customer content.
