---
title: Portal overview
sidebar_label: Overview
---

# Portal overview

Solvable uses four portals over one governed control plane. Each portal has a separate route family, onboarding policy, role model, and set of safe actions.

| Portal | Registration | Main tasks |
|---|---|---|
| User | Email or phone verification | Playground, models, API keys, usage, privacy, installed agents |
| Organization Admin | Email or phone verification with admin context | Members, roles, budgets, billing, tenant policy, installed agents |
| Platform Admin | Provisioned only | Providers, global routing, pricing, security, observability, audit |
| Agent Creator | Email or phone verification with creator context | Marketplace listings, manifests, tests, review, releases, settlements |

A portal page may be publicly reachable so that users can discover it, but protected data and actions require a session with the appropriate role. The Platform Admin surface is intentionally not part of normal public registration.
