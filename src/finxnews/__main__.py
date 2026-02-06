"""CLI entry-point: ``python -m finxnews run`` / ``python -m finxnews email``."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

from finxnews import config
from finxnews.emailer import send_newsletter
from finxnews.pipeline import run_pipeline

logger = logging.getLogger(__name__)


def _latest_newsletter(profile: str) -> Path | None:
    """Return the most recently modified newsletter .md in the profile output dir."""
    paths = config.profile_paths(profile)
    out_dir = paths["output_dir"]
    if not out_dir.exists():
        return None
    mds = sorted(out_dir.glob("newsletter-*.md"), key=lambda p: p.stat().st_mtime)
    return mds[-1] if mds else None


def _send_latest(profile: str) -> None:
    """Send the most recent newsletter for *profile* via email."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    md_path = _latest_newsletter(profile)
    if md_path is None:
        logger.error(
            "No newsletter found for profile '%s' in %s",
            profile,
            config.profile_paths(profile)["output_dir"],
        )
        sys.exit(1)

    if not config.email_enabled():
        logger.error(
            "Email not configured. Set SMTP_USERNAME, SMTP_PASSWORD, "
            "and EMAIL_TO in .env"
        )
        sys.exit(1)

    body = md_path.read_text(encoding="utf-8")
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"TWEETER {profile.upper()} DIGEST — {now}"

    logger.info("Sending %s (%d chars) …", md_path.name, len(body))
    send_newsletter(
        smtp_host=config.SMTP_HOST,
        smtp_port=config.SMTP_PORT,
        username=config.SMTP_USERNAME,
        password=config.SMTP_PASSWORD,
        to_addrs=config.EMAIL_TO,
        subject=subject,
        body_text=body,
    )
    logger.info("Done.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="finxnews",
        description="Daily digest from X Recent Search.",
    )
    sub = parser.add_subparsers(dest="command")

    # ── run ────────────────────────────────────────────────────────────
    run_parser = sub.add_parser("run", help="Execute the daily pipeline.")
    run_parser.add_argument(
        "--profile",
        choices=["finance", "startup"],
        default="finance",
        help="Which config profile to run (default: finance).",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and rank but skip LLM summarisation and newsletter write.",
    )

    # ── email ─────────────────────────────────────────────────────────
    email_parser = sub.add_parser(
        "email",
        help="Email the most recent newsletter for a profile.",
    )
    email_parser.add_argument(
        "--profile",
        choices=["finance", "startup"],
        default="finance",
        help="Which profile's latest newsletter to send (default: finance).",
    )

    args = parser.parse_args(argv)

    if args.command == "run":
        run_pipeline(profile=args.profile, dry_run=args.dry_run)
    elif args.command == "email":
        _send_latest(profile=args.profile)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
