"""``captain builder`` — build (and optionally push) the Docker builder image."""

from __future__ import annotations

import logging

import click

from captain.click._main import cli, common_options, resolve_project_dir
from captain.config import Config
from captain.docker import obtain_builder

log = logging.getLogger(__name__)


@cli.command(
    "builder",
    short_help="Build the Docker builder image and optionally push it.",
)
@common_options
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="Push the built image to a registry after building.",
)
def builder_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    builder_registry: str | None,
    builder_repository: str | None,
    builder_image: str,
    push: bool,
) -> None:
    """Build the Docker builder image used by other build stages.

    By default the image is built locally only.  Pass --push  to also push the image to a
    remote container registry.

    \b
    Examples
    --------
      captain builder
      captain builder --no-cache
      captain builder --push
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
        builder_push=push,
    )

    # 1. Build the image.
    obtain_builder(cfg)
    log.info("Builder image '%s' is ready.", cfg.builder_image)
