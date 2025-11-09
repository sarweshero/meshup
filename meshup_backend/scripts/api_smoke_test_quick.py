#!/usr/bin/env python
"""Quick-start wrapper around the full Meshup API smoke test."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.api_smoke_test import APISmokeTester  # type: ignore  # noqa: E402


def run_steps(tester: APISmokeTester, step_names: Iterable[str]) -> bool:
    """Execute a subset of smoke-test steps in order."""
    success = True
    try:
        for name in step_names:
            step = getattr(tester, name, None)
            if step is None:
                tester._record(name, False, detail="Unknown step requested")  # noqa: SLF001
                success = False
                break
            if not step():
                success = False
                break
    finally:
        tester.print_summary()
    return success


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a quick Meshup API smoke test")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("MESHUP_API_BASE", "http://localhost:8000/api/v1"),
        help="Base URL for the Meshup API (default: %(default)s)",
    )
    parser.add_argument("--email", help="Reuse an existing account email for the smoke test")
    parser.add_argument("--password", help="Password for the provided account")
    parser.add_argument(
        "--mode",
        choices=("quick", "full"),
        default="quick",
        help="Run the trimmed quick flow or the full end-to-end script",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-step diagnostics during execution",
    )
    return parser.parse_args(argv)


QUICK_STEPS: tuple[str, ...] = (
    "register_user",
    "login_user",
    "refresh_access_token",
    "create_server",
    "create_channel",
    "create_message",
    "fetch_channel_messages",
    "logout_user",
)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    tester = APISmokeTester(args.base_url, args.email, args.password, verbose=args.verbose)

    if args.mode == "full":
        return 0 if tester.run() else 1

    return 0 if run_steps(tester, QUICK_STEPS) else 1


if __name__ == "__main__":
    sys.exit(main())
