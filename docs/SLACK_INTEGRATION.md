# Slack Integration

## Overview
The Slack integration provides a foundation for validating credentials, retrieving workspace information, and listing channels using the Slack Web API. OAuth, token persistence, message synchronization, and reporting are intentionally deferred to later phases.

## Service Layer
`app/services/slack_service.py` implements `SlackService` using Slack SDK's `AsyncWebClient`.

### Capabilities
- **Credential validation**: `test_auth()` calls Slack's `auth.test` endpoint and returns workspace/bot metadata without exposing tokens.
- **Workspace info**: `get_workspace_info()` validates credentials and returns team details with `connected` status.
- **Channel retrieval**: `get_channels()` uses `conversations.list` with support for public/private channels, configurable page size, and automatic pagination following `response_metadata.next_cursor`. Never silently truncates results.
- **Error handling**: Custom exceptions (`SlackAuthError`, `SlackPermissionError`, `SlackRateLimitError`, `SlackServiceError`) preserve error types without logging tokens. Failures are never converted into empty successful responses.

### Configuration
- `SLACK_BOT_TOKEN`: Bot User OAuth Token (required to instantiate service)
- `SLACK_API_TIMEOUT`: Request timeout in seconds (default: 30.0)

Credentials are not required for application startup - validation only occurs when integration operations are invoked.

## Required Permissions (Scopes)
Based on the methods implemented:
- `channels:read` / `groups:read` for public/private channel listing (via `conversations.list` with appropriate types)
- `users:read` and general auth scope sufficient for `auth.test`

Actual required scopes depend on workspace configuration and whether private channels are accessed.

## API Endpoints
All endpoints are under `/api/v1/slack` (as configured in the app).

- `GET /api/v1/slack/status` or `GET /api/v1/slack/connection` - Check connection status and workspace info
- `GET /api/v1/slack/workspaces` - List connected workspaces (returns workspace info if connected)
- `GET /api/v1/slack/channels` - List available Slack channels with pagination handled by service
- `POST /api/v1/slack/channels/select` - **Placeholder (no persistence)** for channel selection

### Error Responses
- `401 Unauthorized`: Missing or invalid token
- `403 Forbidden`: Missing required permissions/scopes
- `429 Too Many Requests`: Rate limited by Slack API
- `502 Bad Gateway`: Other Slack API or network errors

## Testing
Tests use mocked Slack clients (`AsyncMock`) - no real credentials or external API calls required.
- Service tests: auth validation (success/invalid/missing scope/network), pagination, empty results, rate limits, missing token
- API tests: endpoint behavior with missing tokens, mocked services, and error status mapping (401/403/429/502)

## Deferred Features (Not Implemented)
- Slack OAuth authorization/callback flow
- Token encryption and persistent storage
- Workspace/channel persistence in database
- Message history synchronization
- Thread reconstruction workflows
- Incremental sync/background jobs
- AI report generation/scheduling
- Frontend/Electron/Mobile changes
