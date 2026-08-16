# Provider Disablement Runbook

**Author:** Farruh  
**Purpose:** Remove an unhealthy or unsafe provider/model from routing without taking down the platform.

## 1. Trigger conditions

Use this runbook for sustained provider outage, credential rejection, unacceptable latency, quota exhaustion, data-policy concern, security incident, invalid responses, or billing anomaly. Confirm the issue is not an isolated client validation error.

## 2. Disable safely

1. Open an incident and record provider, endpoint, model, region, reason, and evidence.
2. Check active route policies and identify affected organizations/projects.
3. Set the provider endpoint or model to `disabled` or `quarantined` in the catalog, depending on the risk.
4. Activate a tested route policy that removes the provider and uses only approved fallbacks.
5. Confirm budget, residency, masking, capability, and model restrictions still hold.
6. Verify new route decisions exclude the provider.
7. Monitor error rate, latency, fallback rate, cost, and customer impact.

## 3. Credential incident

If credentials may be compromised, revoke or disable them at the provider, rotate the secret through the secret manager, verify the new secret with a bounded health check, and do not re-enable the provider until security approves. Search logs, repositories, CI artifacts, images, and tickets for exposure indicators without copying the secret into new evidence.

## 4. Restore

After provider health and credentials are verified, run a synthetic capability test, confirm data-policy metadata and pricing are current, re-enable in staging, and canary a small approved cohort. Restore normal routing only after dashboards and billing evidence are healthy.

## 5. Acceptance evidence

Keep the catalog change, policy version, approver, route samples before/after, provider health checks, credential rotation record if relevant, customer impact, and rollback state.
