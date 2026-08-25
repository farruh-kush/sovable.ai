"""Billing Service internal API routes.

Author: Farruh
"""

from fastapi import APIRouter

from .generations import router as generations_router
from .usage import router as usage_router

internal_router = APIRouter()
internal_router.include_router(usage_router)
internal_router.include_router(generations_router)
