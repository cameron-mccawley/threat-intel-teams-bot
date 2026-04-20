# Threat Intel Teams Bot

This bot polls multiple threat-intel RSS feeds plus the Ransomwatch JSON feed and posts qualifying alerts to a Microsoft Teams webhook.

## Prerequisites

- Python 3.x

## Setup

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy environment template and set values:
   ```bash
   cp .env.example .env
   ```
5. Set `TEAMS_WEBHOOK_URL` in `.env` (required).

## Run

Recommended:
```bash
python3 ThreatIntelBot.py
```

Optional auto-restart wrapper:
```bash
python3 script_starter.py
```

## Configuration (`.env`)

- `TEAMS_WEBHOOK_URL` (required)
- `SQLITE_DB_PATH` (optional, default: `prev_articles.db`)
- `POLL_INTERVAL_SECONDS` (optional, default: `180`)
- `MAX_WORKERS` (optional, default: `5`)
- HTTP timeout is fixed at 15 seconds per request in code.
- `RESTART_TIMER_SECONDS` (optional, default: `5`)
- `BOT_SCRIPT_PATH` (optional, default: `./ThreatIntelBot.py`)
- `CLEANUP_SCRIPT_PATH` (optional, default: `./cleanup_db.py`)

## Database notes

- The bot creates SQLite DB/table automatically on startup if missing.
- Deduplication is stored in SQLite table:
  - `PREV_ARTICLES(source TEXT PRIMARY KEY, added_at TEXT NOT NULL DEFAULT current_timestamp)`
- Cleanup script removes entries older than 30 days using `added_at`.
- `*.db` files are ignored by git by default.

## Security

Never commit real webhook URLs or other secrets. Keep secrets only in `.env`.
