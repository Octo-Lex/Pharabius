# Pharabius Platform v2.2

Hosted artifact visibility and CI ingestion for Pharabius.

## Quick Start

```bash
# Start the platform
cd platform
docker compose up -d

# Upload an artifact bundle
ai-debt upload --url http://localhost:8000 --token YOUR_ADMIN_TOKEN
```

## Architecture

```text
pharabius/        CLI tool (pip install pharabius)
platform/
├── backend/      FastAPI + PostgreSQL
├── frontend/     React + Vite
└── storage/      Content-addressed bundle storage
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/health` | None | Health check |
| POST | `/api/v1/bundles` | Token | Upload artifact bundle |
| GET | `/api/v1/repositories` | None | List repositories |
| GET | `/api/v1/repositories/{id}` | None | Repository detail |
| GET | `/api/v1/repositories/{id}/findings` | None | Findings list |
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

v2.2 uses two token types:

| Token | Purpose |
|-------|---------|
| `ADMIN_TOKEN` (env var) | Full access to all endpoints |
| `phar_*` API key | Upload-only access for CI |

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

## Bundle Storage

Uploaded `.ai-debt` tarballs are stored by content hash (SHA-256):

```text
platform/storage/bundles/
  └── {hash_prefix}/{full_hash}.tar.gz
```

Duplicate bundles (same content) are not re-stored. The database record
points to the existing file.

**Warning:** `.ai-debt` artifacts may contain source-derived evidence
snippets, file paths, hashes, and analysis metadata. Review bundle
contents before uploading to shared platforms.

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
