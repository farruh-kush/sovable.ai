---
title: Authentication
sidebar_label: Authentication
---

# Authentication

Solvable supports email and phone verification for User, Organization Admin, and Agent Creator registration. Google and Apple sign-in can be enabled for configured portal flows. Platform Admin access is provisioned separately and should use stronger controls such as mandatory MFA and step-up verification.

## Sessions

The web portal stores a first-party session token in the browser and uses refresh-token rotation. Logout revokes the refresh token and clears local browser state. API clients should use scoped API keys rather than browser session tokens.

## Role boundaries

A registration request includes an account context. `user` creates a User Portal identity, `admin` creates an Organization Admin identity, and `creator` creates an Agent Creator identity. The backend checks the role again when a login verification code is consumed. A user cannot become an admin by changing a URL or request payload.

## Recovery and linking

Recovery requires a verified channel and should not reveal whether an account exists. Linking a provider requires an authenticated session and step-up verification. Provider subject identifiers, not email text alone, are the durable identity link.
