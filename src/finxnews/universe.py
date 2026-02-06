"""Load finance universe files and build X query strings."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def _load_lines(path: str | Path) -> list[str]:
    """Read a text file and return non-empty, non-comment lines."""
    p = Path(path)
    if not p.exists():
        logger.warning("File not found, skipping: %s", p)
        return []
    lines: list[str] = []
    for raw in p.read_text().splitlines():
        stripped = raw.strip()
        # Allow files to include @handles; X query uses from:handle without @.
        if stripped.startswith("@"):
            stripped = stripped[1:].strip()
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def _kw_clause(keywords: list[str]) -> str:
    return " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords)


def _firm_clause(firms: list[str]) -> str:
    return " OR ".join(f'"{f}"' if " " in f else f for f in firms)


def _acct_clause(accounts: list[str]) -> str:
    return " OR ".join(f"from:{a}" for a in accounts)


def _rebuild_query(
    *,
    keywords: list[str],
    firms: list[str],
    accounts: list[str],
    filters: str,
) -> str:
    parts: list[str] = []
    if keywords:
        parts.append(f"({_kw_clause(keywords)})")
    if firms:
        parts.append(f"({_firm_clause(firms)})")
    if accounts:
        parts.append(f"({_acct_clause(accounts)})")
    query_body = " ".join(parts)
    return f"{query_body} {filters}".strip()


def load_queries(queries_path: Path) -> dict[str, str]:
    """Parse ``queries.yml`` and return a dict of group-name → X query string.

    Each group may reference:
    - ``keywords``: list of search terms
    - ``firms_file``: path to a firm-name file (relative to the profile dir)
    - ``accounts_file``: path to an accounts file (relative to the profile dir)
    - ``filters``: raw filter suffix (e.g. ``lang:en -is:retweet``)
    """
    with open(queries_path) as fh:
        cfg: dict[str, Any] = yaml.safe_load(fh)

    # File references inside queries.yml are relative to its own directory
    base_dir = queries_path.resolve().parent
    groups: dict[str, Any] = cfg.get("groups", {})
    built: dict[str, str] = {}

    for name, group in groups.items():
        # Keywords → OR-joined
        keywords: list[str] = list(group.get("keywords", []) or [])

        # Firms file → OR-joined, quoted when multi-word
        firms: list[str] = []
        firms_file: str | None = group.get("firms_file")
        if firms_file:
            firms = _load_lines(base_dir / firms_file)

        # Accounts file → (from:a OR from:b …)
        accounts: list[str] = []
        accounts_file: str | None = group.get("accounts_file")
        if accounts_file:
            accounts = _load_lines(base_dir / accounts_file)

        if not (keywords or firms or accounts):
            logger.warning("Skipping empty query group: %s", name)
            continue

        # X Recent Search has a 512-char query limit on Basic tier;
        # truncate gracefully if needed.
        filters: str = group.get("filters", "")
        full_query = _rebuild_query(
            keywords=keywords, firms=firms, accounts=accounts, filters=filters
        )

        if len(full_query) > 512:
            logger.warning(
                "Query for '%s' is %d chars (limit 512); truncating keywords.",
                name,
                len(full_query),
            )
            # Truncate in a stable order: keywords → firms → accounts.
            # This keeps the query valid and guarantees we don't exceed X limits.
            while len(full_query) > 512:
                if len(keywords) > 1:
                    keywords.pop()
                elif len(firms) > 1:
                    firms.pop()
                elif len(accounts) > 1:
                    accounts.pop()
                else:
                    break
                full_query = _rebuild_query(
                    keywords=keywords, firms=firms, accounts=accounts, filters=filters
                )

            if len(full_query) > 512:
                logger.warning(
                    "Query for '%s' could not be reduced under 512 chars; skipping group.",
                    name,
                )
                continue

        built[name] = full_query
        logger.debug("Query [%s]: %s", name, full_query)

    return built
