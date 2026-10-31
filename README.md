# Auto-Reporter for Slack Teams

AI-driven, local-first application that connects to Slack workspaces, synchronizes conversations, and generates structured, evidence-based reports.

[![CI](https://github.com/Vishwa-manikandan/auto-reporter-slack-teams/actions/workflows/ci.yml/badge.svg)](https://github.com/Vishwa-manikandan/auto-reporter-slack-teams/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Status:** Active development on `refactor/architecture-cleanup`. Core backend features are implemented and tested.

## Overview

Auto-Reporter converts Slack conversations into structured daily and weekly reports. It identifies decisions, action items, blockers, project updates, and key discussions with traceable source references. Reports are generated using configurable AI providers and persisted for review.

## Features & Implementation Status

### Slack Integration
| Feature | Status | Notes |
| --- | --- | --- |
| Workspace OAuth connection | Implemented | Secure state validation, single-use tokens |
| Token encryption at rest | Implemented | Fernet encryption |
| Token revocation | Implemented | Via Slack `auth.revoke` |
| Channel discovery & selection | Implemented | Public and private channels |
| Message synchronization | Implemented | Pagination, incremental sync, checkpoints |
| Thread reconstruction | Implemented | Parent/reply relationships |
| Webhook signature verification | Implemented | HMAC-SHA256 with timestamp validation |

### AI Processing
| Feature | Status | Notes |
| --- | --- | --- |
| AI provider abstraction | Implemented | `app/services/ai_provider.py` |
| OpenAI-compatible providers | Implemented | OpenAI, OpenRouter compatible |
| Anthropic (Claude) | Implemented | Via Anthropic API |
| Ollama (local) | Implemented | Local model support |
| Mock provider (testing) | Implemented | Default for development |
| Structured output validation | Implemented | Pydantic schemas |
| Source message references | Implemented | Traceability preserved |
| Prompt injection protection | Partially implemented | Basic safeguards in place |

### Reporting
| Feature | Status | Notes |
| --- | --- | --- |
| Daily reports | Implemented | From persisted messages |
| Weekly reports | Implemented | Aggregated across period |
| Executive summaries | Implemented | AI-generated |
| Decisions, action items, blockers | Implemented | Evidence-based extraction |
| Project updates & follow-ups | Implemented | With source references |
| Report persistence | Implemented | SQLAlchemy models |
| Report history & listing | Implemented | With filters/pagination |
| Report regeneration | Implemented | Preserves history safely |
| Report deletion | Implemented | API endpoint available |

### Review & Publishing
| Feature | Status | Notes |
| --- | --- | --- |
| Report preview | Not implemented | Planned |
| Human approval workflow | Not implemented | Planned |
| Publishing integrations | Not implemented | Planned |
| Public distribution | Not implemented | Planned |

### Desktop & Platform
| Feature | Status | Notes |
| --- | --- | --- |
| FastAPI backend | Implemented | `app/main.py` |
| Cross-platform desktop (Electron) | Partially implemented | Scaffold in `electron/`, `packages/desktop/` |
| Microsoft Teams integration | Not implemented | Planned (repo name references Teams) |
| Mobile app | Not implemented | Not present in repository |

## How It Works

1. **Connect** - Install Slack app and authorize via OAuth
2. **Sync** - Select channels and synchronize messages/threads with incremental updates
3. **Analyze** - AI processes conversations with thread context and chunking
4. **Generate** - Create structured reports with evidence and source references
5. **Store** - Persist reports in database for history and retrieval
6. **Review** *(Planned)* - Human review and approval before publishing

## Architecture

```
Slack API → OAuth Service → Sync Service → Database → AI Provider → Report Generator → REST API
```

**Key Components:**
- `app/api/` - FastAPI routes
- `app/services/` - Business logic
- `app/models/` - SQLAlchemy models
- `app/core/` - Config, schemas, utilities
- `app/db/` - Database session

## Technology Stack

| Layer | Technology | Verified |
| --- | --- | --- |
| Backend Framework | FastAPI | Yes |
| Language | Python 3.9+ | Yes |
| Database | SQLite / PostgreSQL compatible | Yes |
| ORM | SQLAlchemy | Yes |
| Validation | Pydantic | Yes |
| AI Providers | OpenAI, Anthropic, Ollama | Yes |
| Slack Integration | slack-sdk | Yes |
| Encryption | cryptography (Fernet) | Yes |
| Testing | pytest | Yes |
| CI/CD | GitHub Actions | Yes |

## Installation & Setup

```bash
git clone https://github.com/Vishwa-manikandan/auto-reporter-slack-teams.git
cd auto-reporter-slack-teams
python -m venv venv
source venv/bin/activate  # or venv\Scriptsctivate on Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`

## Testing

```bash
pytest -q
```

## License

MIT License - see [LICENSE](LICENSE)
