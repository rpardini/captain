"""``captain iso`` — build a bootable ISO image for the specified flavor and architecture."""

from __future__ import annotations

import logging

import click

import captain.flavor
from captain import artifacts
from captain.click._main import cli, common_options, resolve_project_dir
from captain.click._stages import (
    _build_iso_stage,
)
from captain.config import Config

log = logging.getLogger(__name__)


@cli.command(
    "iso",
    short_help="Build ISO image only. Part of build.",
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
    "--iso-mode",
    envvar="ISO_MODE",
    default="docker",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="ISO build stage execution mode (docker, native, skip).",
)
@click.option(
    "--force-iso",
    envvar="FORCE_ISO",
    is_flag=True,
    default=False,
    help="Force ISO rebuild even if outputs already exist.",
)
def build_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    verbose: bool,
    builder_image: str,
    no_cache: bool,
    iso_mode: str,
    force_iso: bool,
) -> None:
    """Run the CaptainOS ISO build."""
    _configure_logging(verbose)

    proj = resolve_project_dir(project_dir)

    cfg = Config(
        project_dir=proj,
        output_dir=proj / "out",
        arch=arch,
        flavor_id=flavor_id,
        builder_image=builder_image,
        no_cache=no_cache,
        iso_mode=iso_mode,
        force_iso=force_iso,
    )

    # Instantiate the flavor
    captain.flavor.create_and_setup_flavor_for_id(cfg.flavor_id, cfg)

    _build_iso_stage(cfg)
    artifacts.collect_iso(cfg)
    log.info("ISO build complete!")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("captain").setLevel(level)
