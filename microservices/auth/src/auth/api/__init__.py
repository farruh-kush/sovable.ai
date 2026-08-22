"""Auth Service API routes.
Author: Farruh
"""
from fastapi import APIRouter
from .keys import router as keys_router
from .validate import router as validate_router
from .identity import router as identity_router

internal_router = APIRouter()
internal_router.include_router(validate_router)
internal_router.include_router(keys_router, prefix="/keys")
public_router = APIRouter()
public_router.include_router(identity_router)
