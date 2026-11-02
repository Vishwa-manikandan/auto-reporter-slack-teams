# Backend Foundation

## Configuration
- Pydantic Settings with environment variable support
- `.env` for local development
- CORS configurable via environment
- Separate Slack and AI credentials

## Database
- SQLAlchemy 2.x compatible
- SQLite connection args only for SQLite URLs
- Session lifecycle managed with dependency injection
- Real health check via `SELECT 1`

## Health Check
- `GET /health` performs actual DB connectivity test
- Returns `healthy` with `database: ok` on success (HTTP 200)
- Returns `unhealthy` with `database: error` on failure (HTTP 503)
- Database failures are mocked in tests without affecting developer database

## Testing
- Use `tests/` with pytest
- In-memory SQLite for isolated tests
- **Verified locally:** `python -m pytest -q` → 28 passed in local verification (2025-10-31)
- Test coverage includes configuration, database, models, and API endpoints
- GitHub Actions status not verified in this pass

## Notes
- Tests pass locally as verified above; continuous integration status not claimed.
