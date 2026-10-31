# Auto-Reporter for Slack Teams

Auto-Reporter is a tool for extracting and summarizing Slack conversations into actionable reports.

## Current Implementation Status

### Implemented and Tested
- **FastAPI Backend**: Core API structure with health checks, database models, and dependency injection
- **Database Foundation**: SQLAlchemy models and session management with SQLite support
- **Slack Integration Foundation**: Async Slack service using `AsyncWebClient` with credential validation (`auth.test`), workspace info retrieval, and paginated channel listing. API endpoints under `/api/v1/slack/` with proper error handling (401/403/429/502). Tests use mocked Slack clients.
- **Configuration**: Pydantic Settings with environment variable support
- **Testing**: Comprehensive test suite (26 tests passing locally)

### Partially Implemented
- **CLI (`autoreporter/`)**: Basic CLI structure exists
- **Report Generation**: Report generator code exists but not fully integrated
- **AI Provider**: Mock provider implemented; real BharatCode integration not fully configured

### Placeholder/Not Implemented
- **Slack OAuth**: Not implemented
- **Persistent Token Storage**: Not implemented
- **Message Synchronization**: Not implemented
- **Thread Reconstruction (full sync workflow)**: Basic methods exist in service but full sync not implemented
- **Scheduled Reports**: Not implemented
- **Electron Desktop App**: Code exists in `packages/desktop/` and `electron/` but not fully integrated
- **Slack Plugin**: Scaffolded only
- **Mobile App**: Scaffolded only

## Setup

```bash
# Create virtual environment
python -m venv .venv
# Activate (Windows)
.venv\Scripts\activate
# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Run server
uvicorn app.main:app --reload
```

## API Docs
Open http://127.0.0.1:8000/docs

## Tests
```bash
pytest -q
```

*Tests are run locally; CI status not verified in this branch.*
