# Figma Canvas Plan

Author: Farruh

## Design direction

Use the attached Solvable reference as the visual anchor: paper background, navy control-plane surfaces, gold governance accents, green trust states, compact monospace eyebrow labels, rounded enterprise cards, and a marketplace rail that feels like a governed app store. The design should remain light, calm, and operational rather than resembling a consumer social network.

## Canvas structure

| Canvas section | Required frames |
|---|---|
| Foundations | Colors, typography, spacing, radius, shadows, icons, status labels, payment badges |
| Public entry | Landing, four portal cards, architecture overview, marketplace preview |
| Platform Admin | Controller login, overview, providers, routing, models/pricing, security, audit |
| Organization Admin | Admin login/register, organization overview, members/RBAC, budgets, billing, policy, installed agents |
| User Portal | User login/register, overview, playground, API keys, models, usage, billing, team, privacy, security |
| Agent Creator | Creator login/register, marketplace, Creator Studio, permissions, test suite, review queue, releases, settlement |
| State library | Loading, empty, error, unauthorized, expired session, payment pending, payment failed, refund, review requested |
| Responsive | Desktop 1440, tablet 1024, mobile 390 for each portal shell |

## Component rules

Portal shells share the brand mark, route-aware title, account switcher, and notification treatment but use different accent labels. Platform Admin uses a darker operations tone. Organization Admin uses gold governance accents. User Portal uses blue/green trust accents. Agent Creator uses brass and teal marketplace accents.

Payment components show `UZS`, `HUMO`, `UZCARD`, `VISA`, and `MASTERCARD` as method badges. Marketplace cards show verification, permissions, supported languages, pricing, installs, and organization eligibility. Destructive or financially consequential actions require confirmation and an explicit audit reason.

## Figma update rule

Do not change the core Solvable concept without approval. Add the four portal frames and the marketplace/payment states to the existing Solvable-AI file. If the Figma write integration is unavailable, preserve this plan locally and use it as the source of truth for the implementation; do not invent a competing visual system.
