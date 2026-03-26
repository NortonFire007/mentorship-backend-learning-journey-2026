# Mentorship Backend Learning Journey 2026

Event-driven Alerts Platform. Users manage subscriptions via FastAPI, while background workers process data and dispatch notifications. Built as a progressive backend mentorship track.

## Project Structure

- `services/api`: FastAPI application with asynchronous database support.
- `docker-compose.yml`: Local infrastructure setup (PostgreSQL + API).

## Getting Started

### Prerequisites

- **Python 3.13** or higher.
- **[uv](https://docs.astral.sh/uv/)** (recommended package manager).
- **Docker** and **Docker Compose**.

### Environment Setup

Create an `.env` file from the provided example:

```powershell
cp .env.example .env
```

Ensure the environment variables match your local or Docker configuration.

---

## Option 1: Local Development (with `uv`)

This method is recommended for interactive coding and fast reloads.

1. **Install Dependencies**:
   From the root directory:
   ```powershell
   uv sync
   ```

2. **Virtual Environment (Optional Manual Setup)**:
   While `uv sync` manages this automatically, you can manually create and activate:
   
   **Windows (PowerShell):**
   ```powershell
   uv venv
   . .venv\Scripts\Activate.ps1
   ```

   **Linux / macOS:**
   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. **Run the Database**:
   Verify you have a PostgreSQL instance running locally on port `5432`, or use the one provided by Docker:
   ```powershell
   docker compose up -d postgres
   ```

3. **Run the FastAPI Application**:
   Navigate to the API folder and start the server:
   ```powershell
   cd services/api
   uv run uvicorn src.main:app --reload
   ```

---

## Option 2: Containerized Setup (Docker Compose)

Run the entire stack (API + Database) with a single command:

```powershell
docker compose up --build
```

---

## Verification

Once the application is running, you can access:

- **API Base**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
