"""Cluster ranked tweets into 'stories' by cashtag, firm, or topic bucket."""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path

from finxnews.models import StoryCluster, TweetItem

logger = logging.getLogger(__name__)

_CASHTAG_RE = re.compile(r"\$([A-Z]{1,6})\b")

# Topic bucket fallbacks (order matters — first match wins)
_TOPIC_BUCKETS: list[tuple[str, set[str]]] = [
    (
        "Earnings",
        {
            "earnings", "guidance", "eps", "revenue", "beat", "beats",
            "miss", "misses", "profit", "outlook", "yoy", "qoq",
        },
    ),
    (
        "Macro / Rates / FX",
        {
            "fed", "fomc", "cpi", "pce", "nfp", "ism", "treasury",
            "yields", "curve", "hikes", "dot plot", "dxy", "usdjpy",
            "eurusd", "gbpusd", "2-year", "10-year", "inflation",
            "rate decision",
        },
    ),
    (
        "Firm Moves",
        {
            "stake", "acquires", "acquisition", "merger", "buyout",
            "ipo", "etf", "fund", "launches", "files", "settles",
            "invests",
        },
    ),
]

# Max tweets to keep per cluster
_MAX_PER_CLUSTER = 8


def _load_firms(firms_path: Path) -> list[str]:
    """Load firm names from config file."""
    if not firms_path.exists():
        return []
    firms: list[str] = []
    for line in firms_path.read_text().splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            firms.append(stripped)
    return firms


def _match_firm(text: str, firms: list[str]) -> str | None:
    """Return the first firm name found in the text (case-insensitive)."""
    text_lower = text.lower()
    for firm in firms:
        if firm.lower() in text_lower:
            return firm
    return None


def _match_topic(text: str) -> str:
    """Return the first matching topic bucket label, or 'General'."""
    text_lower = text.lower()
    for label, keywords in _TOPIC_BUCKETS:
        if any(kw in text_lower for kw in keywords):
            return label
    return "General"


def cluster_tweets(
    tweets: list[TweetItem],
    firms_path: Path | None = None,
) -> list[StoryCluster]:
    """Group tweets into story clusters.

    Priority:
    1. Cashtag(s) extracted from text → key = ``$TICKER``
    2. Firm name matched from ``finance_firms.txt`` → key = firm name
    3. Topic bucket (earnings / macro / firm-moves / general)
    """
    firms = _load_firms(firms_path) if firms_path else []

    buckets: dict[str, list[TweetItem]] = defaultdict(list)

    for tweet in tweets:
        # 1. Cashtags
        tags = _CASHTAG_RE.findall(tweet.text)
        if tags:
            key = f"${tags[0]}"  # cluster by primary cashtag
            buckets[key].append(tweet)
            continue

        # 2. Firm name
        firm = _match_firm(tweet.text, firms)
        if firm:
            buckets[firm].append(tweet)
            continue

        # 3. Topic bucket fallback
        topic = _match_topic(tweet.text)
        buckets[topic].append(tweet)

    # Build StoryCluster objects, cap tweets per cluster, compute aggregate score
    clusters: list[StoryCluster] = []
    for key, items in buckets.items():
        # Keep only the top-scoring tweets
        top = sorted(items, key=lambda t: t.score, reverse=True)[:_MAX_PER_CLUSTER]
        agg = sum(t.score for t in top)
        clusters.append(
            StoryCluster(
                key=key,
                label=key,
                tweets=top,
                aggregate_score=agg,
            )
        )

    # Sort clusters by aggregate score descending
    clusters.sort(key=lambda c: c.aggregate_score, reverse=True)
    logger.info("Clustered %d tweets into %d stories", len(tweets), len(clusters))
    return clusters
