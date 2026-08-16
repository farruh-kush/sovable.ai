# Sovereign AI Draw.io Diagrams

These editable diagrams support the sovereign AI masking and LLM-routing report for the AI-Routing-Layer project. Open the `.drawio` files with [diagrams.net / draw.io](https://app.diagrams.net/) and choose **Open Existing Diagram**. The files use standard `mxfile` XML and are intended to remain editable.

| File | Purpose |
| --- | --- |
| `sovereign_ai_architecture.drawio` | High-level architecture showing the five control-plane services, privacy fabric, domestic data/AI zone, external-provider zone, RAG path, agent tool broker, billing, and audit. |
| `sovereign_ai_workflow.drawio` | End-to-end request workflow covering data classification, local-only versus masked external routing, response validation, restoration, audit, and cost metering. |
| `sovereign_ai_privacy_masking_pipeline.drawio` | Detailed masking pipeline: detection ensemble, entity inventory, classification, reversible tokenization, irreversible redaction, encrypted vault, provider boundary, validation, and restore policy. |
| `sovereign_ai_rag_agent_security.drawio` | RAG and agent security blueprint showing ingestion inspection, ACL-aware retrieval, plan validation, tool capability brokerage, sandboxing, human approval, kill switches, and audit. |
| `sovereign_ai_deployment_topology.drawio` | Two-site domestic deployment topology with primary/DR control planes, local data and GPU pools, HSM/KMS, SIEM/WORM audit, replication, and optional controlled egress. |

The diagrams follow the repository architecture guidance: five independent services (`gateway`, `auth`, `router`, `provider`, `billing`) communicate through HTTP REST; `auth_db` and `billing_db` remain isolated; and Redis is represented only as ephemeral state. The diagrams are design artifacts, not a substitute for a production threat model or regulatory review.

**Author:** Farruh
