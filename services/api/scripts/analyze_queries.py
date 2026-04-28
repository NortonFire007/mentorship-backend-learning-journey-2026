import asyncio
import uuid
from sqlalchemy import text, select
from src.db.database import AsyncSessionLocal
from src.domains.subscriptions.models import Subscription
from src.domains.alerts.models import Alert

async def analyze():
    async with AsyncSessionLocal() as session:
        # 1. Simple query on indexed field
        print("\n--- 1. Simple query on indexed field (destination) ---")
        stmt1 = "EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM subscriptions WHERE destination = 'Paris';"
        result1 = await session.execute(text(stmt1))
        for row in result1:
            print(row[0])

        # 2. Complex DISTINCT ON query
        print("\n--- 2. Complex DISTINCT ON query (Latest Alerts) ---")
        # We need to construct the raw SQL for the DISTINCT ON query we use in the repo
        stmt2 = """
        EXPLAIN (ANALYZE, BUFFERS)
        SELECT subscriptions.id, anon_1.id AS alert_id
        FROM subscriptions 
        LEFT OUTER JOIN (
            SELECT DISTINCT ON (alerts.subscription_id) alerts.id, alerts.subscription_id, alerts.created_at
            FROM alerts 
            ORDER BY alerts.subscription_id, alerts.created_at DESC
        ) AS anon_1 ON subscriptions.id = anon_1.subscription_id;
        """
        result2 = await session.execute(text(stmt2))
        for row in result2:
            print(row[0])

if __name__ == "__main__":
    asyncio.run(analyze())
