"""Finance-aware ranking for tweets."""

from __future__ import annotations

import logging
import re

from finxnews.models import TweetItem

logger = logging.getLogger(__name__)

# ── Boost lexicons ─────────────────────────────────────────────────────────
_EARNINGS_KEYWORDS: set[str] = {
    "earnings", "guidance", "eps", "revenue", "beat", "beats", "miss", "misses",
    "raises", "cuts", "lowers", "yoy", "qoq", "profit", "outlook",
}

_MACRO_KEYWORDS: set[str] = {
    "cpi", "pce", "nfp", "fomc", "fed", "ism", "treasury", "yields", "curve",
    "hikes", "dot plot", "dxy", "usdjpy", "eurusd", "gbpusd", "2-year",
    "10-year", "rate decision", "inflation",
}

_FIRM_MOVE_KEYWORDS: set[str] = {
    "stake", "acquires", "acquisition", "merger", "buyout", "ipo",
    "etf", "fund", "launches", "files", "settles", "invests",
}

_CASHTAG_RE = re.compile(r"\$[A-Z]{1,6}\b")

# ── Weights (tuneable) ─────────────────────────────────────────────────────
_W_LIKE = 1.0
_W_RT = 3.0
_W_REPLY = 0.5
_W_QUOTE = 2.0
_W_KEYWORD_BOOST = 5.0
_W_CASHTAG_BOOST = 3.0


def score(item: TweetItem) -> float:
    """Compute a ranking score for a single tweet."""
    m = item.metrics

    engagement = (
        m.like_count * _W_LIKE
        + m.retweet_count * _W_RT
        + m.reply_count * _W_REPLY
        + m.quote_count * _W_QUOTE
    )

    text_lower = item.text.lower()

    keyword_hits = sum(
        1
        for kw in (_EARNINGS_KEYWORDS | _MACRO_KEYWORDS | _FIRM_MOVE_KEYWORDS)
        if kw in text_lower
    )
    keyword_boost = keyword_hits * _W_KEYWORD_BOOST

    cashtag_boost = len(_CASHTAG_RE.findall(item.text)) * _W_CASHTAG_BOOST

    return engagement + keyword_boost + cashtag_boost


def rank(items: list[TweetItem]) -> list[TweetItem]:
    """Score and sort items descending by score (recency as tiebreak)."""
    for item in items:
        item.score = score(item)

    ranked = sorted(
        items,
        key=lambda t: (t.score, t.created_at or ""),
        reverse=True,
    )
    logger.info("Ranked %d items; top score=%.1f", len(ranked), ranked[0].score if ranked else 0)
    return ranked
