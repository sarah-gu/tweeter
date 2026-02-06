"""Unit tests for story clustering."""

from pathlib import Path

from finxnews.cluster import cluster_tweets
from finxnews.models import TweetItem, TweetMetrics


def _make(
    tweet_id: str,
    text: str,
    score: float = 10.0,
) -> TweetItem:
    return TweetItem(
        tweet_id=tweet_id,
        text=text,
        author_username="testuser",
        metrics=TweetMetrics(like_count=5),
        score=score,
    )


class TestClusterTweets:
    def test_cashtag_clusters(self) -> None:
        items = [
            _make("1", "$AAPL beat earnings expectations", score=20),
            _make("2", "$AAPL guidance raised for Q2", score=15),
            _make("3", "$NVDA new chip launch", score=10),
        ]
        clusters = cluster_tweets(items)
        keys = {c.key for c in clusters}
        assert "$AAPL" in keys
        assert "$NVDA" in keys

        aapl = next(c for c in clusters if c.key == "$AAPL")
        assert len(aapl.tweets) == 2

    def test_firm_match(self, tmp_path: Path) -> None:
        firms_file = tmp_path / "firms.txt"
        firms_file.write_text("Goldman Sachs\nJPMorgan\n")

        items = [
            _make("1", "Goldman Sachs launches new ETF", score=12),
            _make("2", "JPMorgan raises stake in fintech", score=8),
        ]
        clusters = cluster_tweets(items, firms_path=firms_file)
        keys = {c.key for c in clusters}
        assert "Goldman Sachs" in keys
        assert "JPMorgan" in keys

    def test_topic_fallback(self) -> None:
        items = [
            _make("1", "CPI came in hot, Fed may pause cuts", score=10),
        ]
        clusters = cluster_tweets(items)
        assert len(clusters) == 1
        assert clusters[0].key == "Macro / Rates / FX"

    def test_empty(self) -> None:
        assert cluster_tweets([]) == []
