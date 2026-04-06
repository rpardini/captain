#!/usr/bin/env python3
"""CaptainOS build system — click-based CLI entry point.

Requires: Python >= 3.13, click, Rich, Docker (unless all stages use native/skip).
Use Astral's ``uv`` to run::

    uv run click_cli.py --help
    uv run click_cli.py builder
    uv run click_cli.py build --arch arm64
    uv run click_cli.py release-publish --target combined

Or, after ``uv pip install -e .``::

    captain --help
"""

import sys

if sys.version_info < (3, 13):
    print("ERROR: Python >= 3.13 is required.", file=sys.stderr)
    sys.exit(1)

try:
    from captain.click_cli import main
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    uv_url = "https://docs.astral.sh/uv/getting-started/installation/"
    print(f"Missing dependencies, use uv to run. See {uv_url}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()

