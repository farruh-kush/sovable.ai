---
title: Platform introduction
sidebar_label: Introduction
---

# Solvable AI

**Solvable is a customer-controlled AI control plane.** It gives organizations one governed interface for models, providers, privacy, routing, usage, billing, and AI applications.

> One gateway. Every model. Complete control.

## What Solvable does

A client sends a request to the unified API. The gateway authenticates the caller, enforces limits, and applies cache policy. The router selects a permitted model and provider. Privacy controls classify and transform sensitive data before an external call. Provider adapters normalize inconsistent upstream APIs. The response returns in one stable shape, while usage and cost events are recorded for analytics and billing.

## Four portals

| Portal | Who uses it | Start here |
|---|---|---|
| User Portal | Users and builders running governed AI work | [User guide](../portals/user.md) |
| Organization Admin | Tenant owners and administrators | [Organization Admin](../portals/organization-admin.md) |
| Platform Admin | Solvable operators | [Platform Admin](../portals/platform-admin.md) |
| Agent Creator | Publishers building marketplace agents | [Creator guide](../creator/overview.md) |

## Core principles

Solvable keeps provider choice behind a replaceable adapter boundary, treats sensitive data as policy-controlled, records billing as append-only events, and makes high-impact actions auditable. Customer-facing documentation describes configured capabilities without claiming that an unconfigured provider or payment method is active.
