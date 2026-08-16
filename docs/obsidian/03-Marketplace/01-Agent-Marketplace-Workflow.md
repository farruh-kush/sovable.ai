# Agent Marketplace Workflow

Author: Farruh

## Product model

The marketplace is a governed AI application store. An agent is a versioned package with a signed manifest, model policy, tool permissions, data scopes, side-effect level, test evidence, publisher identity, and commercial terms. The marketplace should feel approachable like an app store while retaining enterprise controls.

## Lifecycle

| Stage | Owner | Required evidence | Exit condition |
|---|---|---|---|
| Draft | Agent Creator | Package metadata, prompt/runtime contract, icon, category | Creator submits a complete package |
| Automated checks | Platform services | Manifest schema, dependency scan, permission scan, test results | No blocking findings |
| Human review | Marketplace reviewer | Safety, privacy, quality, publisher, licensing review | Reviewer approves or requests changes |
| Published | Platform Admin | Signed release, pricing, compatibility, support policy | Eligible organizations can discover it |
| Installed | Organization Admin | Tenant approval, data policy, scopes, budget | Agent is available to tenant users |
| Run | User or workflow | Request policy, input classification, tool authorization | Evidence and usage event recorded |
| Updated or revoked | Publisher/reviewer/admin | Version diff, rollback or revocation reason | Previous safe version remains available where possible |

## Marketplace experience

The catalog uses a dark rail and light content area inspired by the reference website. The left rail contains Marketplace, Featured, Verified, categories, and the creator identity. The main area contains a search bar, category chips, an editorial hero, and cards with agent name, publisher, short description, verification badge, installs, supported languages, data policy, and an action.

Every card exposes a safe preview before installation. The preview shows requested permissions, model/provider policy, required data sources, storage behavior, side-effect level, price in UZS, refund terms, and the organization controls that remain active after installation.

## Creator Studio

Creator Studio is divided into Define, Permissions, Test, and Submit steps. Define captures name, category, description, supported languages, input/output contract, and screenshots. Permissions declares model access, tools, network destinations, data classes, and side effects. Test captures deterministic fixtures, expected outputs, prompt-injection cases, PII masking cases, and failure behavior. Submit creates a signed review request.

## Commercial flow

An approved agent may be free, paid once, subscription-based, or usage-priced. All prices are expressed in UZS and stored in integer tiyin. Customer charges are recorded as invoices and payment events. Creator settlement is computed from captured payments less platform fee, refunds, adjustments, and required tax metadata. No creator payout is released until identity and payout profile checks are complete.
