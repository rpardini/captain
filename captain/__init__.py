"""captain — CaptainOS build system.

Logging is configured here so that every ``logging.getLogger(__name__)``
call in submodules automatically inherits the Rich console handler.
"""

from __future__ import annotations

import logging
import os
import shutil

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.traceback import install as _install_rich_traceback

# Obtain terminal width
env_columns = shutil.get_terminal_size(fallback=(161, 24)).columns

# Rich console — writes to stderr so log output never pollutes piped stdout.
# Install Rich traceback handler globally (once, at import time).
if os.environ.get("FORCE_COLOR", "0") == "1":
    console: Console = Console(stderr=True, color_system="standard", width=env_columns)
    _install_rich_traceback(console=console, show_locals=False, width=env_columns, suppress=[click])
else:
    console: Console = Console(stderr=True)
    _install_rich_traceback(console=console, show_locals=False, width=None, suppress=[click])


class _StageFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        name = record.name.replace("captain.", "")
        record.__dict__["stage"] = name
        if os.environ.get("CAPTAIN_IN_DOCKER", "") == "docker":
            record.__dict__["stage"] = f"🐳 {name}"
        return super().format(record)


_handler = RichHandler(
    console=console,
    show_time=False,
    show_level=True,
    show_path=True,
    markup=True,  # interprets [braket]stuff[/bracket] in log messages, beware
    rich_tracebacks=True,
    tracebacks_show_locals=False,
    tracebacks_suppress=[click],  # don't wanna see click infra code in traces
)
_handler.setFormatter(_StageFormatter("[bold][cyan]%(stage)s[/cyan][/bold]: %(message)s"))

logging.basicConfig(level="INFO", datefmt="[%X]", handlers=[_handler])
