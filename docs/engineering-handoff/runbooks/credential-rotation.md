# Credential Rotation Runbook

**Author:** Farruh  
**Purpose:** Rotate secrets without leaving stale credentials, breaking service startup, or exposing values.

## 1. Classify the secret

Identify secret owner, environment, consumers, last-use time, expiry, and exposure status. Critical classes include provider keys, registry credentials, database passwords, Redis credentials, session/signing secrets, webhook secrets, connector tokens, and cloud access keys.

## 2. Planned rotation

1. Create a new secret version in the approved secret manager.
2. Grant the new version to the intended workload identity.
3. Deploy or refresh workloads using the new version.
4. Run health, authentication, provider, billing, and streaming smoke tests as applicable.
5. Confirm old-version use has stopped in access logs and secret-manager metadata.
6. Revoke or disable the old secret.
7. Record rotation time, owner, evidence, and next due date.

## 3. Emergency rotation

For suspected exposure, immediately disable the old credential at its source, disable affected provider/app access, preserve evidence without reproducing the value, rotate dependent secrets if trust relationships are unclear, and monitor for unauthorized use. Invalidate sessions or API keys when session/signing material may be compromised.

## 4. Kubernetes verification

```bash
kubectl -n ai-routing get externalsecret
kubectl -n ai-routing rollout restart deployment/gateway
kubectl -n ai-routing rollout status deployment/gateway --timeout=300s
kubectl -n ai-routing get pods
```

Use the affected service only; do not restart the whole cluster unnecessarily. Verify that secret values do not appear in pod descriptions, events, logs, images, or frontend assets.

## 5. Special cases

Database password rotation may require overlapping credentials or a controlled maintenance window. Session/signing rotation can invalidate active sessions and must have customer communication. Registry rotation must verify image pulls before revoking the old credential. Provider-key rotation must include a bounded health check and quota/budget validation.

## 6. Post-rotation checks

Search repository and CI artifacts for accidental exposure, inspect access logs, confirm old credential rejection, verify service metrics and errors, update the secret inventory, and schedule the next rotation. If a value was exposed in a public channel, treat it as compromised even if no misuse is observed.
