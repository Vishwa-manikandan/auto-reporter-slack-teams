# Architecture Inventory

## Project Structure

### FastAPI Backend (`app/`)
- `app/main.py` - Application entry point
- `app/core/config.py` - Configuration management
- `app/db/session.py` - Database session
- `app/models/` - SQLAlchemy models (8 models)
- `app/api/` - API routes (auth, slack, sync, reports)
- `app/services/` - Business logic (slack_service, sync_service, report_generator, ai_provider)

### CLI Engine (`autoreporter/`, `packages/core/autoreporter/`)
- Keyword detection, Slack client, aggregation, reporting

### Slack Plugin (`packages/slack-plugin/`)
- Slack Bolt app with slash commands

### Desktop App (`packages/desktop/`)
- Electron app with UI

### Mobile App (`packages/mobile/`)
- React Native app

### Infrastructure
- `Dockerfile`, `docker-compose.yml`
- `requirements.txt`, `setup.py`
- Tests in `tests/`
