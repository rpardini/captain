"""``captain tools`` — download tools (containerd, runc, nerdctl, CNI plugins)."""

from __future__ import annotations

import logging

import click

from captain.cli._main import CliContext, cli
from captain.cli._stages import _build_tools_stage

log = logging.getLogger(__name__)


@cli.command(
    "tools",
    short_help="Download tools (containerd, runc, nerdctl, CNI).",
)
@click.option(
    "--tools-mode",
    envvar="TOOLS_MODE",
    default="docker",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="Tools download stage execution mode (docker, native, skip).",
)
@click.option(
    "--force-tools",
    envvar="FORCE_TOOLS",
    is_flag=True,
    default=False,
    help="Re-download tools even if outputs already exist.",
)
@click.pass_obj
def tools_cmd(
    cli_ctx: CliContext,
    *,
    tools_mode: str,
    force_tools: bool,
) -> None:
    """Download tools (containerd, runc, nerdctl, CNI plugins).

    Fetches pre-built binaries for the target architecture and stages
    them under ``mkosi.output/tools/{arch}/``.  The tools are later
    merged into the initramfs by mkosi via ``--extra-tree``.

    \b
    Examples
    --------
      captain tools
      captain tools --arch arm64
      captain tools --tools-mode native
      captain tools --force-tools
    """

    cfg = cli_ctx.make_config(
        tools_mode=tools_mode,
        force_tools=force_tools,
    )

    _build_tools_stage(cfg)
    log.info("Tools stage complete!")
