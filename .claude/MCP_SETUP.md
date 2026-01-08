# MCP Server Setup Guide

## Required Environment Variables

Before using the MCP servers, you need to configure the following environment variables:

### For GCP Services (Firestore, GCS, BigQuery)

```bash
# Option 1: Service Account JSON file
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"

# Option 2: If using gcloud CLI authentication
gcloud auth application-default login
```

### For Slack

```bash
export SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
```

### For Gemini AI (Optional)

If you want to enable the `gcp-ai` server, add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "gcp-ai": {
      "type": "stdio",
      "command": "python",
      "args": ["tools/gcp_ai/mcp_server.py"],
      "env": {
        "GEMINI_API_KEY": "${GEMINI_API_KEY}"
      }
    }
  }
}
```

Then set:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

## Local Development Setup

1. **Create a `.env` file** in the project root:

```bash
# .env (DO NOT COMMIT)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
SLACK_BOT_TOKEN=xoxb-xxx
GEMINI_API_KEY=xxx  # Optional
```

2. **Load environment variables** before starting Claude Code:

```bash
# Using direnv (recommended)
echo 'dotenv' > .envrc
direnv allow

# Or manually
source .env
```

## Available MCP Servers

| Server | Required Env Vars | Description |
|--------|-------------------|-------------|
| `firestore` | `GOOGLE_APPLICATION_CREDENTIALS` | Firestore database operations |
| `gcs` | `GOOGLE_APPLICATION_CREDENTIALS` | Cloud Storage operations |
| `bigquery` | `GOOGLE_APPLICATION_CREDENTIALS` | BigQuery analysis |
| `slack` | `SLACK_BOT_TOKEN` | Slack API |
| `gcloud` | (uses gcloud CLI auth) | GCP CLI operations |

## Troubleshooting

### Error: "GEMINI_API_KEY environment variable not set"

This means you're trying to use the `gcp-ai` server without setting the API key. Either:
1. Set the `GEMINI_API_KEY` environment variable, or
2. Remove the `gcp-ai` server from `.claude/settings.json`

### Error: "Could not automatically determine credentials"

Your GCP credentials are not configured. Run:
```bash
gcloud auth application-default login
```

Or set `GOOGLE_APPLICATION_CREDENTIALS` to point to a service account JSON file.

### Server fails to start

Check that:
1. Python dependencies are installed: `pip install -r requirements.txt`
2. The MCP server file exists at the specified path
3. Required environment variables are set
