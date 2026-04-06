"""``captain builder`` — build (and optionally push) the Docker builder image."""

from __future__ import annotations

import logging

import click

from captain.click_cli._main import cli, common_options, resolve_project_dir
from captain.config import Config
from captain.docker import build_builder
from captain.util import run

log = logging.getLogger(__name__)


@cli.command(
    "builder",
    short_help="Build the Docker builder image, optionally push it.",
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
    "--push",
    is_flag=True,
    default=False,
    help="Push the built image to a registry after building.",
)
@click.option(
    "--registry",
    envvar="REGISTRY",
    default=None,
    help="Registry hostname (e.g. ghcr.io). Required when --push is set.",
)
@click.option(
    "--registry-path",
    envvar="REGISTRY_PATH",
    default=None,
    help="Repository path within the registry (e.g. tinkerbell/captain/builder).",
)
@click.option(
    "--tag",
    "push_tag",
    default=None,
    help="Tag to apply when pushing (default: Dockerfile content hash).",
)
def builder_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    verbose: bool,
    builder_image: str,
    no_cache: bool,
    push: bool,
    registry: str | None,
    registry_path: str | None,
    push_tag: str | None,
) -> None:
    """Build the Docker builder image used by other build stages.

    By default the image is built locally only.  Pass --push together
    with --registry and --registry-path to also push the image to a
    remote container registry.

    \b
    Examples
    --------
      captain builder
      captain builder --no-cache
      captain builder --push --registry ghcr.io --registry-path tinkerbell/captain/builder
      captain builder --push --registry ghcr.io --registry-path tinkerbell/captain/builder --tag lt
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
    )

    # 1. Build the image.
    build_builder(cfg)
    log.info("Builder image '%s' is ready.", cfg.builder_image)

    # 2. Optionally push.
    if push:
        if not registry or not registry_path:
            raise click.UsageError(
                "--registry and --registry-path are required when --push is set."
            )
        import hashlib

        if push_tag is None:
            # Use the Dockerfile content hash (same logic as docker.py)
            dockerfile = cfg.project_dir / "Dockerfile"
            push_tag = hashlib.sha256(dockerfile.read_bytes()).hexdigest()

        full_ref = f"{registry}/{registry_path}:{push_tag}"
        log.info("Pushing builder image → %s", full_ref)

        # Tag and push.
        run(["docker", "tag", cfg.builder_image, full_ref])
        run(["docker", "push", full_ref])
        log.info("Push complete: %s", full_ref)


def _configure_logging(verbose: bool) -> None:
    """Set the captain logger level based on the --verbose flag."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("captain").setLevel(level)
