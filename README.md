# finxnews — Daily Finance & Startup Digest from X

A Python pipeline that pulls posts from the X (Twitter) Recent Search API,
deduplicates and ranks them, clusters posts into stories, generates LLM-written
TL;DR summaries, and outputs a Markdown newsletter — optionally emailed to you.

## Quick start

```bash
# 1. Clone & set up
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set X_BEARER_TOKEN and LLM_API_KEY

# 3. Run
python -m finxnews run --profile finance
python -m finxnews run --profile startup
# Output: out/<profile>/newsletter-YYYYmmdd-HHMMSSZ.md
```

## Profiles

| Profile | Focus |
|---|---|
| `finance` | Earnings, macro/rates/FX, finance-firm moves |
| `startup` | AI models, AI startup funding, AI infra & tools |

Each profile has its own config directory under `config/profiles/<name>/` with
query definitions, firm/org watchlists, and curated accounts.

## Configuration

| Env var | Required | Description |
|---|---|---|
| `X_BEARER_TOKEN` | Yes | X API v2 Bearer Token (read-only) |
| `LLM_API_KEY` | Yes | API key for the LLM provider |
| `LLM_PROVIDER` | No | `openai` (default) |
| `LLM_MODEL` | No | `gpt-4o-mini` (default) |
| `FINXNEWS_MAX_RESULTS` | No | Results per query, 10-100 (default 50) |
| `FINXNEWS_OUTPUT_DIR` | No | Output base dir (default `out`) |
| `FINXNEWS_DB_DIR` | No | SQLite dir (default `var`) |

### Email (optional)

Set all three to have the newsletter emailed after each run:

| Env var | Description |
|---|---|
| `SMTP_USERNAME` | Gmail address (also used as "From") |
| `SMTP_PASSWORD` | Gmail app password |
| `EMAIL_TO` | Recipient address |
| `SMTP_HOST` | SMTP server (default `smtp.gmail.com`) |
| `SMTP_PORT` | SMTP port (default `587`) |

### Watchlists

Edit the plain-text files in `config/profiles/<profile>/` to tune coverage:

- `queries.yml` — query groups (keywords, filters, file refs)
- `*_firms.txt` / `*_firms.txt` — firm/org names for clustering
- `curated_accounts.txt` — high-signal X accounts

## Architecture

```
X Recent Search API
        │
        ▼
  ┌───────────┐
  │  Fetcher   │  (multiple query groups)
  └─────┬─────┘
        ▼
  ┌───────────┐
  │  SQLite    │  (dedupe by tweet ID, per-profile)
  └─────┬─────┘
        ▼
  ┌───────────┐
  │  Ranker    │  (engagement + finance keyword boosts)
  └─────┬─────┘
        ▼
  ┌───────────┐
  │ Clusterer  │  (group by cashtag / firm / topic)
  └─────┬─────┘
        ▼
  ┌───────────┐
  │ LLM TL;DR │  (per-cluster + daily summary)
  └─────┬─────┘
        ▼
  out/<profile>/newsletter-*.md
        │
        ▼ (optional)
     📧 Email
```

## GitHub Actions

The included workflow (`.github/workflows/daily.yml`) runs both profiles daily
and uploads newsletter artifacts. It also emails the newsletter if SMTP secrets
are configured.

Add these repository secrets:

- `X_BEARER_TOKEN`
- `LLM_API_KEY`
- `SMTP_USERNAME` (optional — Gmail address)
- `SMTP_PASSWORD` (optional — Gmail app password)
- `EMAIL_TO` (optional — recipient)

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check src/ tests/
```

## License

MIT
