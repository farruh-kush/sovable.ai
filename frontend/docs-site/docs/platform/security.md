---
title: Security model
sidebar_label: Security
---

# Security model

Security is a control-plane property rather than a single login screen. Solvable separates user, organization-admin, agent-creator, and platform-controller authority. Every service validates its own authorization boundary and treats provider, agent, and client payloads as untrusted input.

## Secrets

Provider keys, registry credentials, signing keys, database passwords, and OAuth secrets belong in managed secret storage. They must not appear in Markdown, generated OpenAPI examples, CI logs, images, browser bundles, or support tickets. The API reference masks credential-like parameters.

## Agent threats

Agent packages are reviewed for prompt injection, unsafe tool use, exfiltration, excessive permissions, unbounded side effects, malicious dependencies, and data-retention mismatch. Runtime execution uses declared permissions and organization policy. A package cannot elevate its own scope.

## Privacy

Sensitive input is classified and masked before provider dispatch. Ordinary logs contain metadata and sanitized errors, not raw prompts. Exports and analytics follow retention and tenant-boundary rules.

## Change controls

High-impact changes—provider disablement, routing policy activation, role escalation, payment activation, marketplace revocation, and secret rotation—require an explicit operator, reason, audit event, and verification step.
