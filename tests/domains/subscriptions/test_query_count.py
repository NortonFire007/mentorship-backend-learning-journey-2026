import pytest
from sqlalchemy import event, select
from src.domains.subscriptions.models import Subscription
from src.domains.alerts.models import Alert
from src.domains.subscriptions.repository import SubscriptionRepository
from tests.factories import UserFactory, SubscriptionFactory, AlertFactory

@pytest.mark.asyncio
async def test_list_with_latest_alert_query_count(db_session):
    # 1. Setup: Create a user with multiple subscriptions, each having multiple alerts
    user = await UserFactory.acreate(db_session)
    
    # Subscription 1: 3 alerts
    sub1 = await SubscriptionFactory.acreate(db_session, user=user)
    await AlertFactory.acreate(db_session, subscription=sub1, price_found=100)
    await AlertFactory.acreate(db_session, subscription=sub1, price_found=90)
    latest_alert1 = await AlertFactory.acreate(db_session, subscription=sub1, price_found=80) # Latest
    
    # Subscription 2: 2 alerts
    sub2 = await SubscriptionFactory.acreate(db_session, user=user)
    await AlertFactory.acreate(db_session, subscription=sub2, price_found=200)
    latest_alert2 = await AlertFactory.acreate(db_session, subscription=sub2, price_found=150) # Latest
    
    # Subscription 3: No alerts
    sub3 = await SubscriptionFactory.acreate(db_session, user=user)
    
    await db_session.commit()
    
    # 2. Query Count Setup
    query_count = 0
    
    @event.listens_for(db_session.bind.sync_engine, "before_cursor_execute")
    def count_queries(conn, cursor, statement, parameters, context, executemany):
        if statement.strip().upper().startswith("SELECT"):
            nonlocal query_count
            query_count += 1
            print(f"SQL SELECT Query: {statement}")
    
    # 3. Execution
    repo = SubscriptionRepository(db_session)
    results = await repo.list_with_latest_alert(user.id)
    
    # 4. Assertions
    assert len(results) == 3
    
    # Check that we got exactly ONE SELECT query
    assert query_count == 1, f"Expected 1 SELECT query, but got {query_count}"
    
    # Verify data correctness
    for sub_obj in results:
        if sub_obj.id == sub1.id:
            assert len(sub_obj.alerts) == 1
            assert sub_obj.alerts[0].id == latest_alert1.id
        elif sub_obj.id == sub2.id:
            assert len(sub_obj.alerts) == 1
            assert sub_obj.alerts[0].id == latest_alert2.id
        elif sub_obj.id == sub3.id:
            assert len(sub_obj.alerts) == 0

    # Cleanup listener
    event.remove(db_session.bind.sync_engine, "before_cursor_execute", count_queries)
