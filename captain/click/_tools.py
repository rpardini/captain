"""``captain tools`` — download tools (containerd, runc, nerdctl, CNI plugins)."""

from __future__ import annotations

import logging

import click

from captain.click._main import cli, common_options, resolve_project_dir
from captain.click._stages import _build_tools_stage
from captain.config import Config

log = logging.getLogger(__name__)


@cli.command(
    "tools",
    short_help="Download tools (containerd, runc, nerdctl, CNI).",
)
@common_options
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
def tools_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    builder_registry: str | None,
    builder_repository: str | None,
    builder_image: str,
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

    proj = resolve_project_dir(project_dir)

    cfg = Config(
        project_dir=proj,
        output_dir=proj / "out",
        arch=arch,
        flavor_id=flavor_id,
        builder_registry=builder_registry,
        builder_repository=builder_repository,
        builder_image=builder_image,
        tools_mode=tools_mode,
        force_tools=force_tools,
    )

    _build_tools_stage(cfg)
    log.info("Tools stage complete!")
