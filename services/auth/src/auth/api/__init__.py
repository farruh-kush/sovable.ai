"""Auth Service internal API routes.

These endpoints are only accessible from within the private network
(consumed by the Gateway Service).

Author: Farruh
"""

from fastapi import APIRouter

from .keys import router as keys_router
from .validate import router as validate_router

internal_router = APIRouter()
internal_router.include_router(validate_router)
internal_router.include_router(keys_router, prefix="/keys")
