"""CLI entry-point: ``python -m finxnews run``."""

from __future__ import annotations

import argparse
import sys

from finxnews.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="finxnews",
        description="Daily digest from X Recent Search.",
    )
    sub = parser.add_subparsers(dest="command")

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

    args = parser.parse_args(argv)

    if args.command == "run":
        run_pipeline(profile=args.profile, dry_run=args.dry_run)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
