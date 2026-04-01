from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


# Import all models here for Alembic
from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription
