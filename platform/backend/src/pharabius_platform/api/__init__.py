"""API routers package."""

from pharabius_platform.api.health import router as health_router
from pharabius_platform.api.upload import router as upload_router

all_routers = [health_router, upload_router]
