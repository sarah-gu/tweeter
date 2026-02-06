"""Minimal X API v2 Recent Search client (read-only)."""

from __future__ import annotations

import logging
import time
from typing import Any

import requests

from finxnews.models import TweetItem, TweetMetrics

logger = logging.getLogger(__name__)

_RECENT_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# Fields we always request.
_TWEET_FIELDS = "created_at,public_metrics,author_id"
_EXPANSIONS = "author_id"
_USER_FIELDS = "username"


class XClientError(Exception):
    """Raised when the X API returns an unexpected response."""


class XClient:
    """Thin wrapper around ``GET /2/tweets/search/recent``."""

    def __init__(self, bearer_token: str, max_results: int = 50) -> None:
        if not bearer_token:
            raise ValueError("X_BEARER_TOKEN is required but was empty.")
        self._bearer = bearer_token
        self._max_results = min(max(max_results, 10), 100)
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self._bearer}"})

    # ── public ──────────────────────────────────────────────────────────
    def search_recent(self, query: str) -> list[TweetItem]:
        """Execute a single Recent Search query and return parsed items."""
        params: dict[str, Any] = {
            "query": query,
            "max_results": self._max_results,
            "tweet.fields": _TWEET_FIELDS,
            "expansions": _EXPANSIONS,
            "user.fields": _USER_FIELDS,
        }

        data = self._get(params)
        tweets_raw: list[dict[str, Any]] = data.get("data", [])
        if not tweets_raw:
            logger.info("No results for query: %s", query)
            return []

        # Build author-id → username map from expansions
        includes = data.get("includes", {})
        users: list[dict[str, Any]] = includes.get("users", [])
        author_map: dict[str, str] = {u["id"]: u.get("username", "") for u in users}

        items: list[TweetItem] = []
        for raw in tweets_raw:
            pm = raw.get("public_metrics", {})
            items.append(
                TweetItem(
                    tweet_id=str(raw["id"]),
                    text=raw.get("text", ""),
                    author_username=author_map.get(str(raw.get("author_id", "")), ""),
                    created_at=raw.get("created_at"),
                    metrics=TweetMetrics(
                        like_count=pm.get("like_count", 0),
                        retweet_count=pm.get("retweet_count", 0),
                        reply_count=pm.get("reply_count", 0),
                        quote_count=pm.get("quote_count", 0),
                    ),
                )
            )

        logger.info("Fetched %d tweets for query: %s", len(items), query)
        return items

    def fetch_all_groups(
        self, queries: dict[str, str]
    ) -> dict[str, list[TweetItem]]:
        """Run multiple named queries and return results keyed by group name.

        ``queries`` maps group-name → X query string.
        """
        results: dict[str, list[TweetItem]] = {}
        for group_name, query_str in queries.items():
            items = self.search_recent(query_str)
            # Tag each item with its query group
            for item in items:
                item.query_group = group_name
            results[group_name] = items
            # Polite back-off between queries (X rate limits)
            time.sleep(1)
        return results

    # ── private ─────────────────────────────────────────────────────────
    def _get(self, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._session.get(_RECENT_SEARCH_URL, params=params, timeout=30)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            logger.warning("Rate-limited; sleeping %ds", retry_after)
            time.sleep(retry_after)
            resp = self._session.get(_RECENT_SEARCH_URL, params=params, timeout=30)
        if resp.status_code != 200:
            raise XClientError(
                f"X API returned {resp.status_code}: {resp.text[:500]}"
            )
        return resp.json()  # type: ignore[no-any-return]
