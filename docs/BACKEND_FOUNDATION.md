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
- Returns `healthy` with `database: ok` on success
- Returns `unhealthy` with `database: error` on failure

## Testing
- Use `tests/` with pytest
- In-memory SQLite for isolated tests
- All existing tests pass
