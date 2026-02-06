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
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)
    return lines


def load_queries(queries_path: Path) -> dict[str, str]:
    """Parse ``queries.yml`` and return a dict of group-name → X query string.

    Each group may reference:
    - ``keywords``: list of search terms
    - ``firms_file``: path to a firm-name file (relative to project root)
    - ``accounts_file``: path to an accounts file
    - ``filters``: raw filter suffix (e.g. ``lang:en -is:retweet``)
    """
    with open(queries_path) as fh:
        cfg: dict[str, Any] = yaml.safe_load(fh)

    project_root = queries_path.resolve().parent.parent  # config/ -> project root
    groups: dict[str, Any] = cfg.get("groups", {})
    built: dict[str, str] = {}

    for name, group in groups.items():
        parts: list[str] = []

        # Keywords → OR-joined
        keywords: list[str] = group.get("keywords", [])
        if keywords:
            kw_clause = " OR ".join(f'"{kw}"' if " " in kw else kw for kw in keywords)
            parts.append(f"({kw_clause})")

        # Firms file → OR-joined, quoted when multi-word
        firms_file: str | None = group.get("firms_file")
        if firms_file:
            firms = _load_lines(project_root / firms_file)
            if firms:
                firm_clause = " OR ".join(f'"{f}"' if " " in f else f for f in firms)
                parts.append(f"({firm_clause})")

        # Accounts file → (from:a OR from:b …)
        accounts_file: str | None = group.get("accounts_file")
        if accounts_file:
            accounts = _load_lines(project_root / accounts_file)
            if accounts:
                acct_clause = " OR ".join(f"from:{a}" for a in accounts)
                parts.append(f"({acct_clause})")

        if not parts:
            logger.warning("Skipping empty query group: %s", name)
            continue

        # Combine
        query_body = " ".join(parts)

        # X Recent Search has a 512-char query limit on Basic tier;
        # truncate gracefully if needed.
        filters: str = group.get("filters", "")
        full_query = f"{query_body} {filters}".strip()

        if len(full_query) > 512:
            logger.warning(
                "Query for '%s' is %d chars (limit 512); truncating keywords.",
                name,
                len(full_query),
            )
            # Simple truncation: keep reducing keywords until under limit
            while len(full_query) > 512 and keywords:
                keywords.pop()
                kw_clause = " OR ".join(
                    f'"{kw}"' if " " in kw else kw for kw in keywords
                )
                parts[0] = f"({kw_clause})"
                query_body = " ".join(parts)
                full_query = f"{query_body} {filters}".strip()

        built[name] = full_query
        logger.debug("Query [%s]: %s", name, full_query)

    return built
