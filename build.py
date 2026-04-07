#!/usr/bin/env python3
"""CaptainOS build system — click-based CLI entry point.

Requires: Python >= 3.13 and a lot of dependencies; Use Astral's ``uv`` to run::

    uv run build.py --help
    uv run build.py builder
    uv run build.py build --arch arm64
    uv run build.py release-publish --target combined
"""

import sys

if sys.version_info < (3, 13):
    print("ERROR: Python >= 3.13 is required.", file=sys.stderr)
    sys.exit(1)

try:
    from captain.cli import main
except ImportError as exc:
    print(f"ERROR: {exc}", file=sys.stderr)
    uv_url = "https://docs.astral.sh/uv/getting-started/installation/"
    print(f"Missing dependencies, use uv to run. See {uv_url}", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
