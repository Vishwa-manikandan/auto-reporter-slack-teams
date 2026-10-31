# Auto-Reporter for Slack Teams

An AI-driven, local-first application that collects Slack conversations, analyzes them with AI, and generates structured daily and weekly reports.

## Project Status

**Current State:** Active development on `refactor/architecture-cleanup`. Core backend functionality is implemented and tested.

## Overview

Auto-Reporter helps teams automatically summarize their Slack activity into reviewable reports. It connects to Slack workspaces via OAuth, synchronizes messages and threads, uses AI to identify decisions, action items, blockers, and project updates, and persists reports for review.

## Features & Implementation Status

| Category | Feature | Status | Notes |
| --- | --- | --- | --- |
| **Slack Integration** | OAuth workspace connection | Implemented | Secure state, token encryption (Fernet) |
|  | Token storage & revocation | Implemented | Encrypted at rest, revocable |
|  | Channel discovery & selection | Implemented | Public/private channels supported |
|  | Message synchronization | Implemented | Pagination, incremental sync, checkpoints |
|  | Thread reconstruction | Implemented | Parent/reply relationships preserved |
|  | Webhook signature verification | Implemented | HMAC verification added |
| **AI Processing** | Provider abstraction | Implemented | Mock, OpenAI, Anthropic, Ollama |
|  | Structured output validation | Implemented | Pydantic schemas |
|  | Source references | Implemented | Traces to messages |
|  | Prompt injection protection | Partially implemented | Basic handling in place |
| **Reporting** | Daily/Weekly reports | Implemented | Generated from persisted messages |
|  | Decisions, action items, blockers | Implemented | Extracted with evidence |
|  | Report persistence | Implemented | Stored in database |
|  | Report history & regeneration | Implemented | API endpoints available |
| **Review & Publishing** | Report preview/approval | Not implemented | Planned |
|  | Public publishing | Not implemented | Planned |
| **Desktop/Mobile** | Desktop app (Electron) | Partially implemented | Scaffold exists |
|  | Mobile app | Not implemented | Not present |
|  | Microsoft Teams | Not implemented | Planned |

## Architecture

```
Slack Workspace → OAuth → Message Sync → DB (SQLite/Postgres) → AI Provider → Report Generation → API/Storage
```

- **Backend:** FastAPI (`app/`)
- **Models:** SQLAlchemy
- **AI:** Configurable providers via `app/services/ai_provider.py`
- **Slack:** `app/services/slack_service.py`, `app/services/sync_service.py`

## Quick Start

### Prerequisites
- Python 3.9+
- Slack app with appropriate scopes

### Installation
```bash
git clone https://github.com/Vishwa-manikandan/auto-reporter-slack-teams.git
cd auto-reporter-slack-teams
pip install -r requirements.txt
cp .env.example .env
```

### Configuration
Edit `.env` with your Slack and AI credentials. See `.env.example` for all options.

### Run
```bash
uvicorn app.main:app --reload
```

## Testing
```bash
pytest -q
```

## Demo
See `demo/sample_thread.json` for a sample Slack thread fixture.

## Evaluation
See `eval/eval_set.json` for a test set of 20 threads with expected outputs.

## License
MIT License - see [LICENSE](LICENSE)
