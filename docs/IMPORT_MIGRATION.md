# Import Migration Guide - New Architecture Structure

## Overview

The project has been reorganized from a flat structure to a professional microservice architecture. This guide explains the new import patterns and helps with migration.

## Old vs. New Import Paths

### API Gateway Service

**Old**: `from ai_routing_layer.api.routes import router`
**New**: `from ai_routing_layer.services.api_gateway.routes import router`

**Old**: `from ai_routing_layer.api.dependencies import get_principal`
**New**: `from ai_routing_layer.services.api_gateway.dependencies import get_principal`

### Routing Service

**Old**: `from ai_routing_layer.router.engine import RoutingEngine`
**New**: `from ai_routing_layer.services.routing.engine import RoutingEngine`

### Provider Service

**Old**: `from ai_routing_layer.providers.base import BaseProvider`
**New**: `from ai_routing_layer.services.providers.base import BaseProvider`

**Old**: `from ai_routing_layer.providers.openai import OpenAIProvider`
**New**: `from ai_routing_layer.services.providers.openai import OpenAIProvider`

**Old**: `from ai_routing_layer.providers.anthropic import AnthropicProvider`
**New**: `from ai_routing_layer.services.providers.anthropic import AnthropicProvider`

### Billing Service

**Old**: `from ai_routing_layer.billing.service import BillingService`
**New**: `from ai_routing_layer.services.billing.service import BillingService`

### Auth Service

**Old**: `from ai_routing_layer.auth.service import AuthService`
**New**: `from ai_routing_layer.services.auth.service import AuthService`

**Old**: `from ai_routing_layer.auth.rate_limit import RateLimiter`
**New**: `from ai_routing_layer.services.auth.rate_limit import RateLimiter`

### Shared Models

**Old**: `from ai_routing_layer.models import ChatCompletionRequest`
**New**: `from ai_routing_layer.shared.models.core import ChatCompletionRequest`

### Infrastructure / Config

**Old**: `from ai_routing_layer.config import get_settings`
**New**: `from ai_routing_layer.infrastructure.config import get_settings`

### Observability

**Old**: `from ai_routing_layer.observability.logging import configure_logging`
**New**: `from ai_routing_layer.infrastructure.observability.logging import configure_logging`

**Old**: `from ai_routing_layer.observability.metrics import MetricsRegistry`
**New**: `from ai_routing_layer.infrastructure.observability.metrics import MetricsRegistry`

## Automated Migration

Run this script to update imports throughout the codebase:

```bash
#!/bin/bash

# Migration script - update_imports.sh

cd "$(git rev-parse --show-toplevel)"

# Define substitutions
declare -A replacements=(
  ["ai_routing_layer.api"]="ai_routing_layer.services.api_gateway"
  ["ai_routing_layer.router.engine"]="ai_routing_layer.services.routing.engine"
  ["ai_routing_layer.providers"]="ai_routing_layer.services.providers"
  ["ai_routing_layer.billing"]="ai_routing_layer.services.billing"
  ["ai_routing_layer.auth"]="ai_routing_layer.services.auth"
  ["ai_routing_layer.models"]="ai_routing_layer.shared.models.core"
  ["ai_routing_layer.config"]="ai_routing_layer.infrastructure.config"
  ["ai_routing_layer.observability.logging"]="ai_routing_layer.infrastructure.observability.logging"
  ["ai_routing_layer.observability.metrics"]="ai_routing_layer.infrastructure.observability.metrics"
)

# Replace in all Python files
for file in $(find . -name "*.py" -type f); do
  for old in "${!replacements[@]}"; do
    new="${replacements[$old]}"
    sed -i "s|from ${old}|from ${new}|g" "$file"
    sed -i "s|import ${old}|import ${new}|g" "$file"
  done
done

echo "✓ Import migration completed"
```

## File Migration Checklist

- [ ] `src/ai_routing_layer/main.py` - Update imports
- [ ] `src/ai_routing_layer/service.py` - Update imports (core service logic)
- [ ] `src/ai_routing_layer/app_state.py` - Update imports
- [ ] All test files in `tests/` - Update imports
- [ ] Any additional service files - Update imports
- [ ] Documentation examples - Update code examples

## Common Import Patterns

### Service Initialization

**Before**:
```python
from ai_routing_layer.providers.openai import OpenAIProvider
from ai_routing_layer.router.engine import RoutingEngine
from ai_routing_layer.billing.service import BillingService
from ai_routing_layer.auth.service import AuthService
```

**After**:
```python
from ai_routing_layer.services.providers.openai import OpenAIProvider
from ai_routing_layer.services.routing.engine import RoutingEngine
from ai_routing_layer.services.billing.service import BillingService
from ai_routing_layer.services.auth.service import AuthService
```

### Data Models

**Before**:
```python
from ai_routing_layer.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    UsageRecord,
)
```

**After**:
```python
from ai_routing_layer.shared.models.core import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    UsageRecord,
)
```

### API Endpoints

**Before**:
```python
from fastapi import APIRouter
from ai_routing_layer.api.dependencies import get_principal
from ai_routing_layer.api.routes import router as api_router
```

**After**:
```python
from fastapi import APIRouter
from ai_routing_layer.services.api_gateway.dependencies import get_principal
from ai_routing_layer.services.api_gateway.routes import router as api_router
```

## Testing After Migration

After updating imports, run the following to verify everything works:

```bash
# 1. Run import checks
python -c "from ai_routing_layer.services.providers.base import BaseProvider; print('✓ Imports work')"

# 2. Run full test suite
pytest tests/ -v

# 3. Check for import errors
python -m py_compile src/ai_routing_layer/**/*.py

# 4. Start the application
uvicorn ai_routing_layer.main:app --reload
```

## Backward Compatibility (Optional)

If you need to maintain backward compatibility during transition, create compatibility shims:

### `src/ai_routing_layer/api.py`

```python
"""Backward compatibility shim for old import paths."""

from ai_routing_layer.services.api_gateway import *  # noqa

__all__ = [
    "router",
    "dependencies",
]
```

### `src/ai_routing_layer/providers.py`

```python
"""Backward compatibility shim for old import paths."""

from ai_routing_layer.services.providers import *  # noqa

__all__ = [
    "BaseProvider",
    "OpenAIProvider",
    "AnthropicProvider",
]
```

Then gradually migrate by updating imports to use the new paths.

## Troubleshooting

### ModuleNotFoundError: No module named 'ai_routing_layer.api'

**Problem**: Old import path still in use
**Solution**: Update to `from ai_routing_layer.services.api_gateway import ...`

### ImportError: cannot import name 'get_principal' from 'ai_routing_layer.services.api_gateway'

**Problem**: File not moved or import statement incomplete
**Solution**: Verify file exists at `src/ai_routing_layer/services/api_gateway/dependencies.py`

### Circular import errors

**Problem**: Services importing from each other incorrectly
**Solution**: Use dependency injection; services depend on abstractions, not concrete implementations

### Tests failing after migration

**Problem**: Test imports not updated
**Solution**: Run the migration script on test files or update manually

```bash
# Find and update test imports
grep -r "from ai_routing_layer.api import" tests/
grep -r "from ai_routing_layer.providers import" tests/
```

## Import Guidelines for New Code

When adding new features, follow these guidelines:

1. **Service Imports**: Use full service path
   ```python
   from ai_routing_layer.services.billing.service import BillingService
   ```

2. **Shared Models**: Use shared.models.core
   ```python
   from ai_routing_layer.shared.models.core import ChatCompletionRequest
   ```

3. **Infrastructure**: Use infrastructure namespace
   ```python
   from ai_routing_layer.infrastructure.config import Settings
   from ai_routing_layer.infrastructure.observability.metrics import MetricsRegistry
   ```

4. **Avoid Circular Imports**: Use dependency injection
   ```python
   # Bad - circular import risk
   from ai_routing_layer.services.routing.engine import RoutingEngine
   from ai_routing_layer.services.providers.base import BaseProvider
   
   # Good - abstraction-based
   from ai_routing_layer.services.providers.base import BaseProvider
   def init_router(providers: List[BaseProvider]) -> RoutingEngine:
       ...
   ```

## References

- See [SERVICE_ARCHITECTURE.md](SERVICE_ARCHITECTURE.md) for detailed service structure
- See [README.md](../README.md) for project overview
- See project diagrams in `/docs/images/` for visual architecture
