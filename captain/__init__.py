"""captain — CaptainOS build system.

Logging is configured here so that every ``logging.getLogger(__name__)``
call in submodules automatically inherits the Rich console handler.
"""

from __future__ import annotations

import logging
import os

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as _install_rich_traceback

# Rich console — writes to stderr so log output never pollutes piped stdout.
# Install Rich traceback handler globally (once, at import time).
if os.environ.get("FORCE_COLOR", "0") == "1":
    console: Console = Console(stderr=True, color_system="standard", width=160, highlight=False)
    _install_rich_traceback(
        console=console, show_locals=False, width=160, suppress=[click], max_frames=2
    )
else:
    console: Console = Console(stderr=True)
    _install_rich_traceback(
        console=console, show_locals=False, width=None, suppress=[click], max_frames=2
    )


class _StageFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        name = record.name
        record.__dict__["stage"] = name
        if os.environ.get("CAPTAIN_IN_DOCKER", "") == "docker":
            # Running on host: show stage names in blue for visual clarity.
            record.__dict__["stage"] = f"[bold][blue]in-docker[/bold]: [/blue]{name}"
        return super().format(record)


_handler = RichHandler(
    console=console,
    show_time=False,
    show_level=True,
    show_path=True,
    markup=True,  # interprets [braket]stuff[/bracket] in log messages, beware
    rich_tracebacks=True,
    tracebacks_show_locals=False,
    tracebacks_max_frames=2,  # too many frames and we get confused
    tracebacks_suppress=[click],  # don't wanna see click infra code in traces
)
_handler.setFormatter(_StageFormatter("%(stage)s: %(message)s"))

logging.basicConfig(level="DEBUG", datefmt="[%X]", handlers=[_handler])
