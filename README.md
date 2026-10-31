# Auto-Reporter for Slack

Automated Slack report generation with OAuth, message sync, and AI-powered insights.

## Status

| Feature | Status |
| --- | --- |
| Slack OAuth & token encryption | Implemented |
| Channel sync & pagination | Implemented |
| Thread reconstruction | Implemented |
| Report generation (daily/weekly) | Implemented |
| Report persistence | Implemented |
| AI provider (OpenAI-compatible, Anthropic, Ollama) | Implemented |
| Microsoft Teams | Planned |
| Mobile app | Not implemented |

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Set up Slack app, add credentials to .env
uvicorn app.main:app --reload
```

## AI Providers

Set `AI_PROVIDER` in `.env`:
- `mock` - for testing (default)
- `openai` - OpenAI API
- `anthropic` - Anthropic API
- `ollama` - Local Ollama model

See `.env.example` for configuration.

## Documentation

See `docs/` for setup, architecture, and API documentation.
