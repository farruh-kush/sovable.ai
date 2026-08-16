# Solvable AI — Product Vault

Author: Farruh

This vault is the local working set for the Solvable AI control plane. It preserves the attached Solvable visual direction—light enterprise surfaces, navy control-plane chrome, gold governance signals, green trust states, and an agent marketplace inspired by a governed AI app store—while organizing the product into four distinct portals.

## Portal map

| Portal | Primary audience | Registration | Main responsibility |
|---|---|---|---|
| [[02-Portals/01-Platform-Admin]] | Platform operators | No self-registration | Providers, routing, pricing, security, deployments, policy, audit |
| [[02-Portals/02-Organization-Admin]] | Customer organization owners/admins | Yes, organization-admin verification | Members, budgets, API keys, data policy, enabled agents, billing |
| [[02-Portals/03-User-Portal]] | Individual users and builders | Yes, standard-user verification | Playground, models, usage, keys, privacy, installed agents |
| [[02-Portals/04-Agent-Creator]] | Agent publishers and developers | Yes, creator verification | Agent packages, permissions, tests, review, releases, settlements |

## Key product rules

Solvable remains a customer-controlled AI control plane. The four portals are separate experiences over shared governed services; they are not four unrelated products. Platform Admin is isolated from customer registration. Organization Admin controls a tenant boundary. Users operate inside that tenant. Agent Creators publish review-gated packages that organizations may install.

Billing is denominated in Uzbek so'm (`UZS`) by default. The internal ledger stores integer tiyin values. Customer-facing payment methods are modeled as Humo, Uzcard, Visa, and Mastercard through a contracted acquiring provider. No live capture is enabled until merchant credentials, signed callbacks, refund rules, and settlement configuration are present.

## Reference material

- [[01-Product/01-Reference-Style]]
- [[02-Portals/00-Portal-Architecture]]
- [[03-Marketplace/01-Agent-Marketplace-Workflow]]
- [[04-Payments/01-UZS-Payment-Architecture]]
- [[05-Operations/01-Release-Workflow]]
- [[06-Design/01-Figma-Canvas-Plan]]
- [[Templates/Portal-Feature-Note]]
