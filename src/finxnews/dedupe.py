"""Deduplication logic — filter out tweets already seen in prior runs."""

from __future__ import annotations

import logging

from finxnews.models import TweetItem
from finxnews.store import TweetStore

logger = logging.getLogger(__name__)


def dedupe(items: list[TweetItem], store: TweetStore) -> list[TweetItem]:
    """Return only tweets whose ID is not already in the store."""
    seen = store.seen_ids()
    new_items = [item for item in items if item.tweet_id not in seen]
    logger.info(
        "Dedupe: %d total → %d new (filtered %d seen)",
        len(items),
        len(new_items),
        len(items) - len(new_items),
    )
    return new_items
