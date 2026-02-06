"""Unit tests for the finance-aware ranker."""

from finxnews.models import TweetItem, TweetMetrics
from finxnews.rank import rank, score


def _make(text: str = "hello", likes: int = 0, rts: int = 0, replies: int = 0) -> TweetItem:
    return TweetItem(
        tweet_id="1",
        text=text,
        metrics=TweetMetrics(
            like_count=likes,
            retweet_count=rts,
            reply_count=replies,
        ),
    )


class TestScore:
    def test_zero_engagement_zero_keywords(self) -> None:
        item = _make("nothing special here")
        assert score(item) == 0.0

    def test_engagement_only(self) -> None:
        item = _make(likes=10, rts=5)
        # 10*1 + 5*3 = 25
        assert score(item) == 25.0

    def test_keyword_boost(self) -> None:
        item = _make("AAPL earnings beat expectations")
        s = score(item)
        # "earnings" + "beat" → 2 keyword hits × 5 = 10
        assert s >= 10.0

    def test_cashtag_boost(self) -> None:
        item = _make("$AAPL is rallying today")
        s = score(item)
        # 1 cashtag × 3 = 3
        assert s >= 3.0

    def test_combined(self) -> None:
        item = _make("$TSLA earnings beat guidance raised", likes=100, rts=50)
        s = score(item)
        # engagement: 100*1 + 50*3 = 250
        # keywords: earnings, beat, guidance, raises → some hits
        # cashtag: $TSLA → 3
        assert s > 250


class TestRank:
    def test_higher_score_first(self) -> None:
        a = _make("boring tweet", likes=1)
        b = _make("$NVDA earnings beat estimates", likes=50, rts=20)
        a.tweet_id = "1"
        b.tweet_id = "2"
        ranked = rank([a, b])
        assert ranked[0].tweet_id == "2"

    def test_empty_list(self) -> None:
        assert rank([]) == []
