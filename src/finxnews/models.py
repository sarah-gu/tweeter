"""Domain models used across the pipeline."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TweetMetrics(BaseModel):
    like_count: int = 0
    retweet_count: int = 0
    reply_count: int = 0
    quote_count: int = 0


class TweetItem(BaseModel):
    tweet_id: str
    text: str
    author_username: str = ""
    created_at: datetime | None = None
    metrics: TweetMetrics = Field(default_factory=TweetMetrics)
    query_group: str = ""
    score: float = 0.0


class StoryCluster(BaseModel):
    key: str  # e.g. "$NVDA", "JPMorgan", "macro"
    label: str = ""
    tweets: list[TweetItem] = Field(default_factory=list)
    aggregate_score: float = 0.0
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)
