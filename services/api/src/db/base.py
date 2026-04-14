from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs


# Define Base here. Models will import this.
class Base(AsyncAttrs, DeclarativeBase):
    pass
