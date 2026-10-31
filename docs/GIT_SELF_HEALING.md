# Git Self-Healing and Repository Recovery

## Overview
Automated recovery for Git/GitHub operations with safety constraints.

## Safety Rules
- Never push to main
- Never force-push
- Never discard uncommitted changes
- Never auto-resolve ambiguous conflicts
- Preserve user data

## Recovery Categories
- Automatically Recoverable: network issues, stale refs
- Recoverable With Verification: divergent branches
- Human Approval Required: conflicts, destructive ops
- Non-Recoverable: auth/permissions

## Usage
Use GitRecoveryService for diagnostics and safe retries.
