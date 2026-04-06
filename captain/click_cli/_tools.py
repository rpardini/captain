"""``captain tools`` — download tools (containerd, runc, nerdctl, CNI plugins)."""

from __future__ import annotations

import logging

import click

from captain import docker, tools
from captain.click_cli._main import cli, common_options, resolve_project_dir
from captain.config import Config

log = logging.getLogger(__name__)


@cli.command(
    "tools",
    short_help="Download tools (containerd, runc, nerdctl, CNI).",
)
@common_options
@click.option(
    "--builder-image",
    envvar="BUILDER_IMAGE",
    default="captainos-builder",
    show_default=True,
    help="Docker builder image name.",
)
@click.option(
    "--no-cache",
    envvar="NO_CACHE",
    is_flag=True,
    default=False,
    help="Rebuild the builder image without Docker layer cache.",
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
def tools_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    verbose: bool,
    builder_image: str,
    no_cache: bool,
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
    _configure_logging(verbose)

    proj = resolve_project_dir(project_dir)

    cfg = Config(
        project_dir=proj,
        output_dir=proj / "out",
        arch=arch,
        flavor_id=flavor_id,
        builder_image=builder_image,
        no_cache=no_cache,
        tools_mode=tools_mode,
        force_tools=force_tools,
    )

    # --- skip ---------------------------------------------------------
    if cfg.tools_mode == "skip":
        log.info("TOOLS_MODE=skip — skipping tools download")
        return

    # --- native -------------------------------------------------------
    if cfg.tools_mode == "native":
        log.info("Downloading tools (nerdctl, containerd, etc.) native...")
        tools.download_all(cfg)
        return

    # --- docker -------------------------------------------------------
    docker.build_builder(cfg)
    log.info("Downloading tools (nerdctl, containerd, etc.) docker...")
    docker.run_in_builder(
        cfg,
        "--entrypoint",
        "/usr/bin/uv",
        cfg.builder_image,
        *(["--verbose"] if log.isEnabledFor(logging.DEBUG) else []),
        "run",
        "/work/build.py",
        "tools",
    )
    docker.fix_docker_ownership(cfg, ["/work/mkosi.output"])

    log.info("Tools command complete!")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("captain").setLevel(level)
