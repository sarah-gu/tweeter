"""Pipeline orchestration — wires fetch → dedupe → rank → cluster → summarise → render."""

from __future__ import annotations

import logging
import sys

from finxnews import config
from finxnews.cluster import cluster_tweets
from finxnews.dedupe import dedupe
from finxnews.llm import LLMSummarizer
from finxnews.models import TweetItem
from finxnews.newsletter import write_newsletter
from finxnews.rank import rank
from finxnews.store import TweetStore
from finxnews.universe import load_queries
from finxnews.x_client import XClient

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )


def run_pipeline(profile: str = "finance", dry_run: bool = False) -> None:
    """Execute the full daily pipeline for the given *profile*."""
    _setup_logging()
    logger.info("=== finxnews pipeline start [profile=%s] ===", profile)

    # ── 0. Resolve profile paths ──────────────────────────────────────
    paths = config.profile_paths(profile)

    # ── 1. Load query config ──────────────────────────────────────────
    queries = load_queries(paths["queries"])
    if not queries:
        logger.error("No queries loaded from %s — nothing to do.", paths["queries"])
        return
    logger.info("Loaded %d query groups", len(queries))

    # ── 2. Fetch tweets ───────────────────────────────────────────────
    client = XClient(bearer_token=config.X_BEARER_TOKEN, max_results=config.MAX_RESULTS)
    results = client.fetch_all_groups(queries)

    all_items: list[TweetItem] = []
    for group_name, items in results.items():
        logger.info("  [%s] fetched %d tweets", group_name, len(items))
        all_items.extend(items)
    logger.info("Total fetched: %d", len(all_items))

    if not all_items:
        logger.warning("No tweets fetched — exiting.")
        return

    # ── 3. Dedupe (per-profile DB) ────────────────────────────────────
    store = TweetStore(db_path=paths["db"])
    new_items = dedupe(all_items, store)

    if not new_items:
        logger.info("All tweets already seen — nothing new today.")
        return

    # ── 4. Rank ───────────────────────────────────────────────────────
    ranked = rank(new_items)

    # ── 5. Store newly seen tweets ────────────────────────────────────
    inserted = store.insert_many(ranked)
    logger.info("Stored %d new tweets", inserted)

    if dry_run:
        logger.info("Dry-run mode — skipping LLM summarisation and newsletter write.")
        for item in ranked[:10]:
            logger.info(
                "  [%.1f] @%s: %s", item.score, item.author_username, item.text[:100]
            )
        return

    # ── 6. Cluster ────────────────────────────────────────────────────
    firms_path = paths["firms"]
    clusters = cluster_tweets(ranked, firms_path=firms_path)

    # ── 7. LLM summarise ─────────────────────────────────────────────
    summarizer = LLMSummarizer(
        provider=config.LLM_PROVIDER,
        api_key=config.LLM_API_KEY,
        model=config.LLM_MODEL,
    )
    for cluster in clusters:
        summarizer.summarize_cluster(cluster)

    daily_tldr = summarizer.daily_tldr(clusters)

    # ── 8. Render newsletter ──────────────────────────────────────────
    query_summary = ", ".join(queries.keys())
    out_path = write_newsletter(
        clusters=clusters,
        daily_tldr=daily_tldr,
        output_dir=paths["output_dir"],
        profile=profile,
        query_summary=query_summary,
    )

    logger.info("=== finxnews pipeline done [profile=%s] — %s ===", profile, out_path)
