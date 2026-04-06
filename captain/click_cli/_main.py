"""Click CLI — main group with shared options and subcommand registration."""

from __future__ import annotations

import functools
import logging
import sys
from pathlib import Path
from typing import Any

import click

from captain.config import DEFAULT_FLAVOR_ID
from captain.flavor import list_available_flavors
from captain.util import detect_current_machine_arch

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared option decorators
# ---------------------------------------------------------------------------


def common_options(fn: Any) -> Any:
    """Decorate a click command with options shared by every subcommand."""

    @click.option(
        "--arch",
        envvar="ARCH",
        default=(detect_current_machine_arch()),
        show_default=True,
        type=click.Choice(["amd64", "arm64"], case_sensitive=False),
        metavar="ARCH",
        help="Target architecture (amd64, arm64).",
    )
    @click.option(
        "--flavor-id",
        envvar="FLAVOR_ID",
        default=DEFAULT_FLAVOR_ID,
        show_default=True,
        type=click.Choice(list_available_flavors(), case_sensitive=False),
        help="Flavor (kernel/board config) to build.",
    )
    @click.option(
        "--project-dir",
        envvar="CAPTAIN_PROJECT_DIR",
        default=None,
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        help="Project root directory (auto-detected when omitted).",
    )
    @click.option(
        "-v",
        "--verbose",
        is_flag=True,
        default=False,
        help="Enable debug-level logging.",
    )
    @functools.wraps(fn)
    def wrapper(**kwargs: Any) -> Any:
        return fn(**kwargs)

    return wrapper


# ---------------------------------------------------------------------------
# Resolve project directory
# ---------------------------------------------------------------------------


def resolve_project_dir(project_dir: str | None) -> Path:
    """Return an absolute ``Path`` for the project root."""
    if project_dir is not None:
        return Path(project_dir)
    # Walk upward from this file until we find pyproject.toml.
    candidate = Path(__file__).resolve().parent.parent.parent
    if (candidate / "pyproject.toml").is_file():
        return candidate
    click.echo("Error: cannot auto-detect project directory. Pass --project-dir.", err=True)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Top-level Click group
# ---------------------------------------------------------------------------

CONTEXT_SETTINGS = dict(
    help_option_names=["-h", "--help"],
    max_content_width=120,
)


@click.group(
    context_settings=CONTEXT_SETTINGS,
    invoke_without_command=True,
    help=(
        "CaptainOS build system.\n\n"
        "Run 'captain COMMAND --help' for details on each subcommand.\n\n"
        "Shell completion (bash/zsh):\n\n"
        '  eval "$(_CAPTAIN_COMPLETE=bash_source captain)"   # bash\n\n'
        '  eval "$(_CAPTAIN_COMPLETE=zsh_source captain)"    # zsh'
    ),
)
@click.version_option(package_name="captain")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """CaptainOS build system — click CLI."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# ---------------------------------------------------------------------------
# Register subcommands (imported lazily to avoid circular imports)
# ---------------------------------------------------------------------------


def main() -> None:
    """Console-script entry point."""
    # Import subcommand modules to register them on the group.
    from captain.click_cli import _build, _builder, _release_publish, _tools  # noqa: F401

    cli()
