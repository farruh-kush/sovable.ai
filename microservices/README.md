# Microservices

**Author:** Farruh

This directory contains the five independently deployable FastAPI services: `auth`, `billing`, `gateway`, `provider`, and `router`. Each service owns its contract, tests, Dockerfile, configuration, and deployment-facing probes. Services communicate over HTTP and do not access another service’s private database.

Run a service’s tests from its own directory, for example `cd microservices/auth && pytest -q`. Build contexts are rooted at the repository root so the shared backend library remains available.
