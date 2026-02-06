"""Centralised configuration loaded from environment variables and dotenv."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUERIES_PATH: Path = Path(
    os.getenv("FINXNEWS_QUERIES_PATH", str(PROJECT_ROOT / "config" / "queries.yml"))
)
DB_PATH: Path = Path(os.getenv("FINXNEWS_DB_PATH", str(PROJECT_ROOT / "var" / "data.sqlite3")))
OUTPUT_DIR: Path = Path(os.getenv("FINXNEWS_OUTPUT_DIR", str(PROJECT_ROOT / "out")))

# ── X API ──────────────────────────────────────────────────────────────────
X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")
MAX_RESULTS: int = int(os.getenv("FINXNEWS_MAX_RESULTS", "50"))

# ── LLM ────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
