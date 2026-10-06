# Clientele

An analytical CRM. A business uploads its sales data and sees which customers
to keep, grow and win back. Many organizations share one deployment, and each
sees only its own data.

## How it fits together

| Piece      | Folder | What it does                                                     |
| ---------- | ------ | ---------------------------------------------------------------- |
| Web app    | `web/` | Next.js screens. Forwards `/api/*` requests to the API.          |
| API        | `api/` | FastAPI. Login, roles, and (later) reads of pre-computed metrics. |
| Worker     | `api/` | Celery, same code as the API. Runs imports and metric jobs.      |
| PostgreSQL |        | All data. Tables are created by Alembic migrations.              |
| Redis      |        | The job queue between the API and the worker.                    |

## Run it locally

You need Docker Desktop.

```sh
cp .env.example .env      # then set JWT_SECRET and POSTGRES_PASSWORD
docker compose up --build
```

Open http://localhost:3000 and create an account. The API's interactive docs
are at http://localhost:8000/docs.

Code changes reload automatically. Everything runs inside Docker, including
`node_modules`, so nothing heavy lands in this folder.

## Tests and linters

```sh
docker compose run --rm api pytest          # API tests (uses a separate crm_test database)
docker compose run --rm api ruff check .    # Python lint
docker compose run --rm api ruff format .   # Python formatting
docker compose run --rm web npm run lint
docker compose run --rm web npm run typecheck
docker compose run --rm web npm run format
```

## Common tasks

```sh
# After changing a model in api/app/models.py, generate a migration and review it:
docker compose run --rm api alembic revision --autogenerate -m "describe the change"
docker compose run --rm api alembic upgrade head

# After adding a JavaScript package (node_modules lives in a Docker volume):
docker compose run --rm web npm install <package>

# Start over with an empty database:
docker compose down -v
```
