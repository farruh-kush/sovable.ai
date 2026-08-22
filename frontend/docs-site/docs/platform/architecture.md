---
title: Architecture
sidebar_label: Architecture
---

# Architecture

```text
Client → Gateway → Policy and privacy → Router → Provider adapter → Model provider
                    ↓                    ↓
                Usage events         Billing ledger
                    ↓
              Analytics and audit
```

The gateway presents a stable OpenAI-compatible interface. The router owns candidate eligibility, scoring, fallback, and route-decision evidence. Provider adapters isolate upstream differences. Billing consumes usage and payment events rather than joining across service databases. The dashboard and documentation surfaces consume control-plane contracts rather than reaching into provider credentials.

## Trust boundaries

Clients and agent packages are untrusted inputs. The gateway authenticates and validates them. Provider APIs are an external boundary. Database and cache stores are internal service boundaries with least-privilege access. Platform Admin actions cross the highest-impact boundary and therefore require role checks, confirmation, audit events, and rollback or disablement procedures.
