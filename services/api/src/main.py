import datetime
from fastapi import FastAPI
from src.core.config import settings
from src.domains.users.router import router as users_router
from src.domains.subscriptions.router import router as subscriptions_router
from src.domains.alerts.router import router as alerts_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG
)

app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(subscriptions_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    """
    Root endpoint for basic connectivity check.
    """
    return {
        "message": "Mentorship Backend API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring systems.
    Returns status and UTC timestamp.
    """
    return {
        "status": "ok",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
