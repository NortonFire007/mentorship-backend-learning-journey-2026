from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
from src.core.events.mixin import EventRecordableMixin


# Define Base here. Models will import this.
class Base(AsyncAttrs, EventRecordableMixin, DeclarativeBase):
    pass
