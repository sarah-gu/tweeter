"""Centralised configuration loaded from environment variables and dotenv."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ── X API ──────────────────────────────────────────────────────────────────
X_BEARER_TOKEN: str = os.getenv("X_BEARER_TOKEN", "")
MAX_RESULTS: int = int(os.getenv("FINXNEWS_MAX_RESULTS", "50"))

# ── LLM ────────────────────────────────────────────────────────────────────
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

# ── Profile defaults (overridden at runtime by CLI) ───────────────────────
DEFAULT_PROFILE: str = os.getenv("FINXNEWS_PROFILE", "finance")
PROFILES_DIR: Path = PROJECT_ROOT / "config" / "profiles"
OUTPUT_BASE: Path = Path(os.getenv("FINXNEWS_OUTPUT_DIR", str(PROJECT_ROOT / "out")))
DB_BASE: Path = Path(os.getenv("FINXNEWS_DB_DIR", str(PROJECT_ROOT / "var")))


def profile_paths(profile: str) -> dict[str, Path]:
    """Return resolved paths for a given profile name.

    Keys: ``profile_dir``, ``queries``, ``firms``, ``accounts``, ``db``, ``output_dir``.
    """
    profile_dir = PROFILES_DIR / profile
    return {
        "profile_dir": profile_dir,
        "queries": profile_dir / "queries.yml",
        "firms": profile_dir / f"{_firms_filename(profile)}",
        "accounts": profile_dir / "curated_accounts.txt",
        "db": DB_BASE / f"{profile}.sqlite3",
        "output_dir": OUTPUT_BASE / profile,
    }


def _firms_filename(profile: str) -> str:
    """Each profile can name its firms file differently."""
    mapping: dict[str, str] = {
        "finance": "finance_firms.txt",
        "startup": "startup_firms.txt",
    }
    return mapping.get(profile, "firms.txt")
