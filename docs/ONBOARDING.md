# CarbonScope Developer Onboarding

Welcome! This guide helps new contributors get up and running quickly.

## Prerequisites

- **Python 3.10+** and **pip**
- **Node.js 18+** and **npm**
- **Docker** (optional, for containerised dev)
- **PostgreSQL 16** (or SQLite for local dev)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/<org>/carbonscope.git
cd carbonscope
```

### 2. Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
pip install -e ".[dev]"
```

Copy the environment template and adjust values:

```bash
cp .env.example .env           # Edit DATABASE_URL, SECRET_KEY, etc.
```

Run database migrations:

```bash
alembic upgrade head
```

Start the API server:

```bash
uvicorn api.main:app --reload
```

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app opens at <http://localhost:3000> and proxies API calls to the
backend on port 8000.

### 4. Running Tests

**Backend** (from repo root):

```bash
python -m pytest tests/ -q --tb=short
```

**Frontend** (from `frontend/`):

```bash
npx vitest run
```

## Project Layout

| Directory      | Purpose                                       |
| :------------- | :-------------------------------------------- |
| `api/`         | FastAPI backend (routes, services, models)    |
| `frontend/`    | Next.js 15 / React 19 frontend                |
| `carbonscope/` | Bittensor protocol, scoring, emission factors |
| `neurons/`     | Miner and validator entry points              |
| `tests/`       | Backend test suite (pytest)                   |
| `k8s/`         | Kubernetes manifests                          |
| `docs/`        | Project documentation                         |
| `alembic/`     | Database migration scripts                    |
| `scripts/`     | Dev & ops helper scripts                      |

## Key Docs

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design and module overview
- [API.md](docs/API.md) — REST API reference
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — production deployment guide
- [CONTRIBUTING.md](docs/CONTRIBUTING.md) — contribution workflow and standards
- [SECURITY.md](docs/SECURITY.md) — security policy and vulnerability reporting
- [CHANGELOG.md](docs/CHANGELOG.md) — version history

## Common Tasks

| Task                      | Command                                        |
| :------------------------ | :--------------------------------------------- |
| Run backend               | `uvicorn api.main:app --reload`                |
| Run frontend              | `cd frontend && npm run dev`                   |
| Run all backend tests     | `python -m pytest tests/ -q`                   |
| Run frontend tests        | `cd frontend && npx vitest run`                |
| Create a DB migration     | `alembic revision --autogenerate -m "message"` |
| Apply migrations          | `alembic upgrade head`                         |
| Build Docker images       | `docker compose build`                         |
| Start with Docker Compose | `docker compose up -d`                         |
| Lint backend              | `ruff check api/ tests/`                       |
| Lint & format frontend    | `cd frontend && npm run lint`                  |

## Getting Help

Open an issue or reach out in the project's communication channel.
