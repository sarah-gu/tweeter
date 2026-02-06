"""LLM-powered summariser — generates per-cluster and daily TL;DR."""

from __future__ import annotations

import logging
from typing import Any

from finxnews.models import StoryCluster

logger = logging.getLogger(__name__)

# ── System prompt used for every summarisation call ────────────────────────
_SYSTEM_PROMPT = (
    "You are a concise finance newsletter writer. "
    "Given a set of tweets about a financial topic, produce:\n"
    "1. A 1–2 sentence summary of the story.\n"
    "2. 3–5 bullet-point takeaways.\n"
    "Be factual. If information is speculative or unconfirmed, note it."
)

_DAILY_SYSTEM_PROMPT = (
    "You are a concise finance newsletter writer. "
    "Given per-story summaries from today's finance Twitter, produce a "
    "daily TL;DR section of 5–10 bullet points capturing the most important "
    "market themes and events of the day. Be brief and factual."
)


class LLMSummarizer:
    """Provider-agnostic summariser. Ships with OpenAI; easily swappable."""

    def __init__(self, provider: str, api_key: str, model: str) -> None:
        self._provider = provider.lower()
        self._api_key = api_key
        self._model = model
        self._client: Any = None

        if not api_key:
            logger.warning("LLM_API_KEY not set — summaries will use fallback stubs.")
            return

        if self._provider == "openai":
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=api_key)
            except ImportError:
                logger.error("openai package not installed; falling back to stubs.")
        else:
            logger.warning("Unknown LLM_PROVIDER '%s'; using stubs.", provider)

    # ── public ──────────────────────────────────────────────────────────

    def summarize_cluster(self, cluster: StoryCluster) -> StoryCluster:
        """Generate summary + bullets for a single cluster."""
        tweet_block = "\n---\n".join(
            f"@{t.author_username}: {t.text}" for t in cluster.tweets
        )
        user_msg = (
            f"Topic/ticker: {cluster.key}\n\n"
            f"Tweets:\n{tweet_block}"
        )

        raw = self._chat(_SYSTEM_PROMPT, user_msg)
        cluster.summary, cluster.bullets = self._parse_summary(raw)
        return cluster

    def daily_tldr(self, clusters: list[StoryCluster]) -> str:
        """Generate the overall daily TL;DR from per-cluster summaries."""
        summaries = "\n\n".join(
            f"**{c.key}**: {c.summary}" for c in clusters if c.summary
        )
        if not summaries:
            return "_No stories to summarise today._"

        raw = self._chat(_DAILY_SYSTEM_PROMPT, summaries)
        return raw

    # ── private ─────────────────────────────────────────────────────────

    def _chat(self, system: str, user: str) -> str:
        """Send a chat-completion request. Falls back to a stub if no client."""
        if self._client is None:
            return self._stub(user)

        if self._provider == "openai":
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=512,
            )
            return resp.choices[0].message.content or ""

        return self._stub(user)

    @staticmethod
    def _stub(user: str) -> str:
        """Fallback when no LLM is available — return a placeholder."""
        return f"(LLM summary unavailable) Preview:\n{user[:300]}…"

    @staticmethod
    def _parse_summary(raw: str) -> tuple[str, list[str]]:
        """Split LLM output into a summary line and bullet list."""
        lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
        summary = ""
        bullets: list[str] = []

        for line in lines:
            if line.startswith(("-", "•", "*")):
                bullets.append(line.lstrip("-•* ").strip())
            elif not summary:
                summary = line

        return summary, bullets
