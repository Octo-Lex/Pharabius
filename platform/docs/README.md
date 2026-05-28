# Pharabius Platform v2.2

Hosted artifact visibility and CI ingestion for Pharabius.

> **v2.2.1 status: working local persistent platform for single-user dev.**
> This is NOT production-ready. See [Known Limitations](#known-limitations).

## Quick Start

```bash
# Start the platform (requires Docker)
cd platform
ADMIN_TOKEN=your-secret docker compose up -d

# Initialize database tables (dev only)
docker compose exec backend python scripts/init_dev_db.py

# Upload an artifact bundle
ai-debt upload --url http://localhost:8000 --token YOUR_ADMIN_TOKEN

# Check health
curl http://localhost:8000/api/v1/health
```

## Data Flow

```text
CI/CLI → POST /api/v1/bundles → validate → parse → persist to PostgreSQL
                                                   ↓
Read endpoints query persisted data:
  GET /repositories        → list repos with latest run
  GET /repositories/{id}   → repo detail
  GET /repositories/{id}/findings → paginated findings
  GET /portfolio           → cross-repo aggregation
  GET /portfolio/risk-rollup → severity distribution
  GET /repositories/{id}/trends → temporal trend points
  GET /repositories/{id}/gate-history → quality gate history
  GET /claims              → claims across repos
  GET /gaps                → gaps across repos
  GET /readiness           → readiness status per repo
```

## Architecture

```text
pharabius/        CLI tool (pip install pharabius)
platform/
├── backend/      FastAPI + SQLAlchemy 2.0 + asyncpg + PostgreSQL 16
├── frontend/     React 19 + Vite 6 (scaffold only)
├── storage/      Content-addressed bundle storage (SHA-256)
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/health` | None | Health check |
| POST | `/api/v1/bundles` | Token | Upload artifact bundle (persists to DB) |
| GET | `/api/v1/repositories` | None | List repositories |
| GET | `/api/v1/repositories/{id}` | None | Repository detail |
| GET | `/api/v1/repositories/{id}/findings` | None | Findings (filterable) |
| GET | `/api/v1/repositories/{id}/runs` | None | Run history |
| GET | `/api/v1/repositories/{id}/latest-run` | None | Latest run |
| GET | `/api/v1/repositories/{id}/trends` | None | Trend points |
| GET | `/api/v1/repositories/{id}/gate-history` | None | Gate history |
| GET | `/api/v1/portfolio` | None | Portfolio summary |
| GET | `/api/v1/portfolio/risk-rollup` | None | Severity distribution |
| GET | `/api/v1/claims` | None | Claims across repos |
| GET | `/api/v1/gaps` | None | Gaps across repos |
| GET | `/api/v1/readiness` | None | Readiness status |
| POST | `/api/v1/api-keys` | Admin | Create API key |
| GET | `/api/v1/api-keys` | Admin | List API keys |
| DELETE | `/api/v1/api-keys/{id}` | Admin | Revoke API key |

## Authentication

v2.2.1 supports two token types:

| Token | Purpose | Storage |
|-------|---------|---------|
| `ADMIN_TOKEN` (env var) | Full access to all endpoints | Environment variable |
| `phar_*` API key | Upload + read access | Database (SHA-256 hashed) |

### CI Upload

```bash
# Create an upload token
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI Upload", "key_type": "upload"}'

# Upload from CI
ai-debt upload --url http://platform.example.com --token phar_YOUR_KEY
```

### Auth rejection cases

- No `Authorization` header → 401
- Wrong admin token → 401
- Invalid API key → 401
- Revoked API key → 401 ("API key has been revoked")
- Expired API key → 401 ("API key has expired")
- Non-`phar_` token that isn't admin → 401

## Bundle Storage

Uploaded `.ai-debt` tarballs are stored by content hash (SHA-256):

```text
platform/storage/bundles/
  └── {hash_prefix}/{full_hash}.tar.gz
```

Duplicate bundles (same content hash) are rejected with 409.
The original tarballs are never discarded.

**Warning:** `.ai-debt` artifacts may contain source-derived evidence
snippets, file paths, hashes, and analysis metadata. Review bundle
contents before uploading to shared platforms.

## Database Setup

### Development (Docker Compose)

```bash
# Start PostgreSQL
docker compose up -d db

# Create tables
cd backend
python scripts/init_dev_db.py
```

### Production (Alembic)

```bash
cd backend
alembic upgrade head
```

The initial migration (`001_initial`) creates 11 tables:
organizations, repositories, artifact_bundles, runs, findings,
quality_gate_results, trend_snapshots, claims, gaps, api_keys.

## Error Responses

All errors use a standard envelope:

```json
{
  "error": {
    "code": "artifact_validation_failed",
    "message": "Missing required artifacts.",
    "details": {},
    "request_id": "abc123"
  }
}
```

## Known Limitations

- **Platform tests are mock-based.** No real PostgreSQL integration tests.
  All 68 platform tests verify route registration, response shapes, and
  ORM model correctness — but NOT actual database queries.
- **Frontend is scaffold only.** No views, no API calls, no Tailwind config.
- **No Docker Compose smoke test.** `docker compose up` has never been run
  against this codebase in CI.
- **No GitHub OAuth / user accounts / RBAC.** Admin token only.
- **No background workers.** Parsing is synchronous within the upload request.
- **No pagination.** All list endpoints return full results.
- **No rate limiting.** No request throttling.
- **No load testing.** Performance under concurrent uploads is unknown.
- **No TLS.** Use a reverse proxy (nginx/caddy) for production.
- **Single-user posture.** No multi-tenancy isolation.

## Deployment

### Docker Compose (development)

```bash
cd platform
ADMIN_TOKEN=your-secret-token docker compose up -d
```

### Production notes

- Set `ADMIN_TOKEN` to a strong secret
- Use managed PostgreSQL instead of Docker
- Configure TLS termination (nginx/caddy)
- Set `STORAGE_PATH` to a persistent volume
- Back up both the database and storage directory regularly
- Run `alembic upgrade head` for schema migrations
