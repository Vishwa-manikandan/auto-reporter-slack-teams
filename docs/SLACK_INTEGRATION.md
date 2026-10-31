# Slack Integration

## Overview
The Slack integration provides a foundation for validating credentials, retrieving workspace information, and listing channels using the Slack Web API. OAuth, token persistence, message synchronization, and reporting are intentionally deferred to later phases.

## Service Layer
`app/services/slack_service.py` implements `SlackService` using Slack SDK's `AsyncWebClient`.

### Capabilities
- **Credential validation**: `test_auth()` calls Slack's `auth.test` endpoint and returns workspace/bot metadata without exposing tokens.
- **Workspace info**: `get_workspace_info()` validates credentials and returns team details with `connected` status.
- **Channel retrieval**: `get_channels()` uses `conversations.list` with support for public/private channels, configurable page size, and automatic pagination following `response_metadata.next_cursor`.
- **Error handling**: Custom exceptions (`SlackAuthError`, `SlackPermissionError`, `SlackRateLimitError`, `SlackServiceError`) preserve error types without logging tokens.

### Configuration
- `SLACK_BOT_TOKEN`: Bot User OAuth Token (required to instantiate service)
- `SLACK_API_TIMEOUT`: Request timeout in seconds (default: 30.0)

## Required Permissions (Scopes)
Based on the methods implemented:
- `channels:read` / `groups:read` for public/private channel listing (via `conversations.list` with appropriate types)
- `users:read` and general auth scope sufficient for `auth.test`

Actual required scopes depend on workspace configuration and whether private channels are accessed.

## API Endpoints
All endpoints are under `/api/slack` (as configured in the app).

- `GET /api/slack/status` or `GET /api/slack/connection` - Check connection status and workspace info
- `GET /api/slack/workspaces` - List connected workspaces (returns workspace info if connected)
- `GET /api/slack/channels` - List available Slack channels with pagination handled by service
- `POST /api/slack/channels/select` - Placeholder for channel selection (no persistence)

### Error Responses
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Missing required permissions/scopes
- `429 Too Many Requests`: Rate limited by Slack API
- `502 Bad Gateway`: Other Slack API or network errors

## Testing
Tests use mocked Slack clients (`AsyncMock`) - no real credentials or external API calls required.
- Service tests: auth validation, pagination, error cases
- API tests: endpoint behavior with missing tokens and mocked services

## Deferred Features (Not Implemented)
- Slack OAuth authorization/callback flow
- Token encryption and persistent storage
- Workspace/channel persistence in database
- Message history synchronization
- Thread reconstruction workflows
- Incremental sync/background jobs
- AI report generation/scheduling
- Frontend/Electron/Mobile changes
