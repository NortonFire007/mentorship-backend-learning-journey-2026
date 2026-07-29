import logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from src.core.config import settings
from src.core.security.password import hash_password
from src.db.database import db_transaction
from src.domains.users.models import User

logger = logging.getLogger(__name__)


async def create_first_superuser() -> None:
    """
    Creates the first superuser if it doesn't exist yet, using credentials
    defined in the configuration/environment settings.
    """
    if not settings.FIRST_SUPERUSER_EMAIL or not settings.FIRST_SUPERUSER_PASSWORD:
        logger.info("First superuser email or password not configured. Skipping initialization.")
        return

    try:
        async with db_transaction() as session:
            # Check if superuser with the configured email already exists
            stmt = select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                logger.info("First superuser already exists in the database.")
                return

            logger.info(f"Creating first superuser: {settings.FIRST_SUPERUSER_EMAIL}")
            superuser = User(
                name="Admin",
                surname="Superuser",
                email=settings.FIRST_SUPERUSER_EMAIL,
                is_superuser=True,
                is_verified=True,
                password_hash=await hash_password(settings.FIRST_SUPERUSER_PASSWORD),
            )
            session.add(superuser)
    except IntegrityError:
        # Handles race conditions under concurrent container startups
        logger.warning(
            "Conflict encountered during superuser creation (IntegrityError). "
            "The superuser was likely created concurrently by another worker process."
        )
    except Exception as e:
        logger.error(f"Failed to create first superuser: {e}", exc_info=True)
