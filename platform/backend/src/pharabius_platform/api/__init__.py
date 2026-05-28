"""API routers package."""

from pharabius_platform.api.api_keys import router as api_keys_router
from pharabius_platform.api.health import router as health_router
from pharabius_platform.api.portfolio import router as portfolio_router
from pharabius_platform.api.repositories import router as repositories_router
from pharabius_platform.api.reviews import router as reviews_router
from pharabius_platform.api.upload import router as upload_router

all_routers = [
    health_router,
    upload_router,
    repositories_router,
    portfolio_router,
    api_keys_router,
    reviews_router,
]
