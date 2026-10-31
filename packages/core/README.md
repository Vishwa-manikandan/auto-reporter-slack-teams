# Auto-Reporter for Slack Teams

AI-driven automation to summarize Slack threads, detect action items and blockers, and generate clean status reports.

## Quick Start (MVP)

```bash
# Install dependencies
pip install -r requirements.txt

# Set env vars
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_CHANNEL_ID=C...

# Generate report
python -m autoreporter --days 1
```

## Features (MVP)
- Polls Slack channel history
- Keyword detection (Bug, Blocked, Action Item, Feature Request)
- Extracts threads and mentions
- Generates structured markdown report
- Local-first - no cloud telemetry
