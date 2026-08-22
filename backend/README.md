# Backend Platform

**Author:** Farruh

This directory contains backend platform code that is shared across services. `shared/` holds stable types, exceptions, serialization, middleware, and logging helpers. The `legacy-*` directories are retained reference/template code and are not part of the production service runtime.

Domain-specific logic belongs in the owning service under `microservices/`; shared code must remain dependency-light and must not contain provider or tenant business decisions.
