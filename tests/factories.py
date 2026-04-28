import factory
import uuid
from faker import Faker
from decimal import Decimal
from datetime import timedelta, date

from src.domains.users.models import User
from src.domains.subscriptions.models import Subscription
from src.domains.alerts.models import Alert
from src.core.enums import TravelType, CurrencyEnum, AlertStatus

fake = Faker()

class AsyncFactoryMixin:
    @classmethod
    async def acreate(cls, session, **kwargs):
        """
        Builds the model instance and persists it to the database asynchronously.
        Filters out kwargs that are not valid model attributes.
        """
        # Get valid model attributes from the factory's Meta
        model_class = cls._meta.model
        valid_keys = {c.key for c in model_class.__table__.columns} if hasattr(model_class, "__table__") else set()
        
        # If it's a SQLAlchemy model, filter. Otherwise pass as is.
        if valid_keys:
            filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_keys or hasattr(model_class, k)}
        else:
            filtered_kwargs = kwargs

        instance = cls.build(**filtered_kwargs)
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

class AlertFactory(factory.Factory, AsyncFactoryMixin):
    """
    Factory for creating Alert instances.
    """
    class Meta:
        model = Alert

    id = factory.LazyFunction(uuid.uuid4)
    subscription = factory.SubFactory(SubscriptionFactory)
    price_found = factory.LazyFunction(lambda: Decimal(fake.random_int(min=100, max=1000)))
    status = AlertStatus.SENT
