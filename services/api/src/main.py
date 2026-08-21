import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from taskiq_dashboard import TaskiqDashboard

from src.core.config import settings
from src.core.taskiq import broker, rabbitmq_broker
from src.core.security.password import generate_dummy_hash
from src.domains.users.router import router as users_router
from src.domains.subscriptions.router import router as subscriptions_router
from src.domains.alerts.router import router as alerts_router
from src.domains.tasks.router import router as tasks_router
from src.domains.auth.router import router as auth_router
from src.domains.webhooks.router import router as webhooks_router
from src.db.init_db import create_first_superuser

from src.core.security.redis_auth import get_redis_client, close_redis

# MCP Admin Server Initialization and Tool Registration (Order is critical!)
from src.domains.mcp_admin.server import mcp
import src.domains.mcp_admin.tools.users  # noqa: F401
import src.domains.mcp_admin.tools.parsers  # noqa: F401



# Initialize Taskiq Dashboard (instantiated early so it is available in lifespan)
dashboard = TaskiqDashboard(
    api_token=settings.TASKIQ_DASHBOARD_TOKEN,
    storage_type="sqlite",
    database_dsn=settings.TASKIQ_DASHBOARD_DB_DSN,
    broker=broker,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Generate dummy hash for timing attack defense
    app.state.dummy_hash = generate_dummy_hash()
    
    # Initialize Redis client pool
    get_redis_client()
    
    # Start taskiq broker connections
    if not broker.is_worker_process:
        await broker.startup()
    if not rabbitmq_broker.is_worker_process:
        await rabbitmq_broker.startup()

    # Seed initial database records (first superuser)
    await create_first_superuser()

    # Execute taskiq-dashboard sub-app lifespan manually since FastAPI mount does not trigger it.
    # IMPORTANT: Only run dashboard lifespan in the API server process, NOT in the worker process.
    # In the worker, dashboard.application.lifespan internally calls broker.startup(), which
    # fires WORKER_STARTUP events again → re-entering this lifespan → infinite recursion.
    if not broker.is_worker_process:
        async with dashboard.application.router.lifespan_context(dashboard.application):
            async with mcp.session_manager.run():
                yield
    else:
        yield

    # Close taskiq broker connections
    if not broker.is_worker_process:
        await broker.shutdown()
    if not rabbitmq_broker.is_worker_process:
        await rabbitmq_broker.shutdown()
        
    # Close Redis connection pool
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(settings.TASKIQ_DASHBOARD_PATH, dashboard.application)
app.mount("/mcp", mcp.get_asgi_app())


app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(subscriptions_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(tasks_router, prefix=settings.API_V1_STR)
app.include_router(webhooks_router, prefix=settings.API_V1_STR)


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
