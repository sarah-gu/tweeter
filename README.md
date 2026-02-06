# finxnews — Daily Finance Digest from X

A Python pipeline that pulls finance-relevant posts from the X (Twitter) Recent
Search API, deduplicates and ranks them, clusters posts into stories, generates
LLM-written TL;DR summaries, and outputs a Markdown newsletter.

## Quick start

```bash
# 1. Clone & set up
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set X_BEARER_TOKEN and LLM_API_KEY

# 3. Run
python -m finxnews run
# Output: out/newsletter.md
```

## Configuration

| Env var | Required | Description |
|---|---|---|
| `X_BEARER_TOKEN` | Yes | X API v2 Bearer Token (read-only) |
| `LLM_API_KEY` | Yes | API key for the LLM provider |
| `LLM_PROVIDER` | No | `openai` (default) |
| `LLM_MODEL` | No | `gpt-4o-mini` (default) |
| `FINXNEWS_MAX_RESULTS` | No | Results per query, 10-100 (default 50) |
| `FINXNEWS_QUERIES_PATH` | No | Path to queries YAML (default `config/queries.yml`) |
| `FINXNEWS_DB_PATH` | No | SQLite path (default `var/data.sqlite3`) |
| `FINXNEWS_OUTPUT_DIR` | No | Output dir (default `out`) |

### Finance watchlists

Edit the plain-text files in `config/` to tune coverage:

- `config/queries.yml` — query groups (keywords, filters, file refs)
- `config/finance_firms.txt` — firm names for story clustering
- `config/curated_accounts.txt` — high-signal X accounts

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
  │  SQLite    │  (dedupe by tweet ID)
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
  out/newsletter.md
```

## GitHub Actions

The included workflow (`.github/workflows/daily.yml`) runs the pipeline daily
and uploads `out/newsletter.md` as an artifact. Add these repository secrets:

- `X_BEARER_TOKEN`
- `LLM_API_KEY`

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check src/ tests/
```

## License

MIT
