---
title: User Portal guide
sidebar_label: User Portal
---

# User Portal guide

Use the User Portal when you need to work with governed AI inside an organization or personal workspace.

## Sign in and register

Open `https://sovable.ai/portal`. Register with a verified email or phone number. The verification context is `user`, so the resulting identity is a standard user rather than an organization administrator or creator.

## Playground

The Playground sends requests through the same gateway used by production applications. Select an eligible model, review the data policy, choose a system instruction, and run the request. The response view shows normalized output, latency, tokens, cache state, and route metadata when the organization permits those details.

## API keys

Create one key per integration. Use descriptive names, scopes, expiration dates, and organization limits. Rotate keys when an owner leaves, a repository is exposed, or a provider policy changes. The key value is shown once.

## Usage and privacy

Usage shows requests, tokens, latency, cache behavior, provider outcomes, and chargeable events. Privacy shows classifications and transformations without exposing raw prompt content. If an input is blocked, the UI explains the policy decision and gives a safe correction path.

## Agents

Users can run agents installed by the organization. They cannot grant new tool permissions, bypass masking, or change a tenant budget. Agent runs are recorded with the agent version, permission scope, model route, and side-effect outcome.
