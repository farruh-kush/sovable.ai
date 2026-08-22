---
title: Create an agent
sidebar_label: Create an agent
---

# Create an agent

Start from the Agent Creator portal at `https://sovable.ai/creator/register`. The creator identity is separate from User and Organization Admin identities.

## Package metadata

Choose a stable name, category, logo, supported languages, short description, long description, support contact, and version. Describe the customer job in plain language. Avoid claims about capabilities that are not covered by tests.

## Runtime contract

Declare the input schema, output schema, context requirements, model aliases, provider constraints, tool calls, network destinations, storage behavior, and timeout expectations. A runtime contract lets the marketplace show organizations what they are installing before execution.

## Permissions

Request only the scopes needed for the job. A permission must identify the resource, action, data classification, and whether the action can create an external side effect. Examples include reading a selected knowledge base, calling a retrieval tool, or drafting an email without sending it.

## Package example

```yaml
name: procurement-copilot
version: 0.1.0
publisher: example-creator
entrypoint: agent.run
permissions:
  models: [qwen-plus]
  data: [organization.procurement.read]
  tools: [search_documents]
  side_effects: draft_only
pricing:
  currency: UZS
  mode: usage
```

The example is illustrative. Provider credentials, secrets, or customer data do not belong in a manifest.
