from fastapi import FastAPI

from ai_routing_layer.api import router
from ai_routing_layer.config import get_settings
from ai_routing_layer.observability.logging import configure_logging

configure_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(router)
