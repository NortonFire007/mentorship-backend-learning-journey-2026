import factory
import uuid
from faker import Faker
from decimal import Decimal
from datetime import timedelta, date

from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription
from src.core.enums import TravelType, CurrencyEnum

fake = Faker()

class AsyncFactoryMixin:
    @classmethod
    async def acreate(cls, session, **kwargs):
        """
        Builds the model instance and persists it to the database asynchronously.
        """
        instance = cls.build(**kwargs)
        session.add(instance)
        await session.flush()
        return instance


class UserFactory(factory.Factory, AsyncFactoryMixin):
    """
    Factory for creating User instances.
    """
    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    name = factory.LazyFunction(fake.first_name)
    surname = factory.LazyFunction(fake.last_name)
    email = factory.LazyAttribute(lambda o: f"{o.name.lower()}.{o.surname.lower()}_{fake.random_int()}@{fake.domain_name()}")
    telegram_id = factory.LazyFunction(lambda: str(fake.random_int(min=10000000, max=99999999)))
    preferred_currency = CurrencyEnum.USD
    is_active = True


class SubscriptionFactory(factory.Factory, AsyncFactoryMixin):
    """
    Factory for creating Subscription instances.
    """
    class Meta:
        model = Subscription

    id = factory.LazyFunction(uuid.uuid4)
    user = factory.SubFactory(UserFactory)
    origin = factory.LazyFunction(fake.city)
    destination = factory.Sequence(lambda n: f"Dest_{n}_{fake.city()}")
    travel_type = TravelType.FLIGHT
    
    start_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=40))
    duration_days = 10
    
    max_price = Decimal("500.00")
    currency = CurrencyEnum.EUR
    is_active = True
