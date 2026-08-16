# Incident Response Runbook

**Author:** Farruh  
**Scope:** Gateway, router, providers, auth, billing, privacy, marketplace, Kubernetes, and data platform.

## 1. Declare and classify

Open an incident record with start time, reporter, severity, affected environment, suspected component, customer impact, and incident commander. Page the responsible owner for Critical and High incidents. Use request IDs and timestamps as evidence; do not paste credentials or raw customer content.

| Severity | Example | Initial target |
|---|---|---:|
| Critical | Public API unavailable, cross-tenant exposure, billing corruption, credential compromise. | Page immediately. |
| High | Major provider outage without effective fallback, sustained SLO burn, privacy block failure. | Page within minutes. |
| Medium | Degraded feature, delayed usage, admin-only outage. | Assign during business hours. |
| Low | Cosmetic issue, isolated non-critical dashboard defect. | Queue and monitor. |

## 2. Stabilize

Confirm whether the problem is platform-wide, tenant-scoped, provider-scoped, or release-scoped. Apply the least destructive mitigation: pause a rollout, disable a provider, activate the previous route policy, revoke a key, freeze an affected budget, reduce concurrency, or scale a safe workload. Do not make unrelated changes during containment.

## 3. Investigate

Use the alert, dashboard, logs, traces, release history, request IDs, route-decision records, provider-attempt records, billing state, privacy decisions, and Kubernetes events. Check for recent deployments, policy activations, secret rotations, certificate changes, node pressure, database/Redis health, and provider status.

## 4. Communicate

Maintain a timeline and an owner for technical mitigation, customer communication, security assessment, and evidence. State known facts, hypotheses, impact, mitigation, and next update time. Avoid sharing secrets, raw prompts, or unverified blame.

## 5. Recover

Verify health, SLOs, billing timeliness, privacy behavior, provider eligibility, and customer-visible flows. Remove temporary mitigations only after evidence supports recovery. Record residual risk and follow-up work.

## 6. Close

Close only after the incident commander records impact, root cause or contributing factors, timeline, detection quality, mitigation, recovery evidence, customer communication, and action items with owners/dates. Run a blameless review for Critical and High incidents.

## 7. Useful commands

```bash
kubectl get pods -A
kubectl -n ai-routing get events --sort-by=.lastTimestamp
kubectl -n ai-routing rollout history deployment/gateway
kubectl -n ai-routing logs deployment/gateway --tail=200
kubectl -n ai-routing logs deployment/router --tail=200
kubectl -n ai-routing logs deployment/provider --tail=200
```

Redact logs before exporting them.
