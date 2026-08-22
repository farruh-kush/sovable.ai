---
title: Review and release
sidebar_label: Review and release
---

# Review and release

A submitted agent enters an evidence-based review pipeline. The creator receives findings and can upload a new version without losing the prior review record.

## Automated checks

The platform validates manifest schema, signed package identity, dependency and artifact safety, declared permissions, test coverage, prompt-injection cases, sensitive-data handling, provider eligibility, and pricing metadata. Blocking findings must be fixed before human review.

## Human review

Reviewers assess whether the agent does what the listing claims, whether its requested permissions are proportionate, whether its data behavior is clear, whether side effects are safe, and whether the support and commercial terms are complete. Approval is tied to a specific version.

## Release operations

A new version is independently tested and approved. Organizations may pin a version or accept a compatible update according to their policy. If a release is unsafe or broken, Platform Admin can revoke it and organizations can roll back to a previous approved version. Rollback does not erase run evidence.
