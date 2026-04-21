# Sprint 1: FastAPI Foundation (Travel Deals Alerts)

## Planned

Set up the main learning repository and build the first FastAPI service with a clean project structure, CRUD endpoints, validation, configuration management, Docker Compose, and basic tests.

## Done

- **FastAPI Foundation**: Created a project structure in `services/api` (core, db, domains).
- **Domain Logic**: Implemented `users` and `subscriptions` domains with full basic CRUD operations.
- **Validation**: Added data validation using Pydantic `field_validator` and `model_validator` (e.g., date logic, amount checks).
- **Configuration**: Set up `pydantic-settings` to manage environment variables via `.env`.
- **Infrastructure**: Configured `docker-compose.yml` with:
  - PostgreSQL database.
  - Automatic Alembic migrations running before API start.
  - API service running on Uvicorn.
- **Testing**: Configured `pytest` with `pytest-asyncio` and `factory-boy` for scalable integration tests.
- **Documentation**: Updated `README.md` with setup instructions and project architecture overview.

## Learned

- Modern package management with `uv`.
- Structuring FastAPI projects for scalability using the "Domains" approach.
- Orchestrating multi-container environments and managing automated migrations.
- Efficient testing patterns using factories and asynchronous fixtures.
