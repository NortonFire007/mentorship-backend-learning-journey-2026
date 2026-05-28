import taskiq_fastapi
from taskiq_redis import RedisStreamBroker, RedisAsyncResultBackend
from taskiq import SimpleRetryMiddleware
from taskiq_dashboard import DashboardMiddleware

from src.core.config import settings

# 1. Limit result TTL to prevent memory leaks in Redis (1 hour = 3600 seconds)
result_backend = RedisAsyncResultBackend(
    redis_url=settings.REDIS_URL,
    result_ex_time=3600,
)

# 2. Use RedisStreamBroker to prevent task loss (requires consumer acknowledgement)
broker = RedisStreamBroker(
    url=settings.REDIS_URL,
).with_result_backend(result_backend)

broker.add_middlewares(
    SimpleRetryMiddleware(default_retry_count=3),
    DashboardMiddleware(
        url=settings.TASKIQ_DASHBOARD_URL,
        api_token=settings.TASKIQ_DASHBOARD_TOKEN,
        broker_name="main_worker"
    )
)

# 3. Initialize the FastAPI integration
taskiq_fastapi.init(broker, "src.main:app")

