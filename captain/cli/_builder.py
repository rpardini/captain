"""``captain builder`` — build (and optionally push) the Docker builder image."""

from __future__ import annotations

import logging

import click

from captain.cli._main import CliContext, cli
from captain.docker import obtain_builder

log = logging.getLogger(__name__)


@cli.command(
    "builder",
    short_help="Build the Docker builder image and optionally push it.",
)
@click.option(
    "--push",
    is_flag=True,
    default=False,
    help="Push the built image to a registry after building.",
)
@click.pass_obj
def builder_cmd(
    cli_ctx: CliContext,
    *,
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
    cfg = cli_ctx.make_config(builder_push=push)

    # 1. Build the image.
    obtain_builder(cfg)
    log.info("Builder image '%s' is ready.", cfg.builder_image)
