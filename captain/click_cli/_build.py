"""``captain build`` — full build pipeline (tools → initramfs → iso → artifacts)."""

from __future__ import annotations

import logging

import click

import captain.flavor
from captain.click_cli._main import cli, common_options, resolve_project_dir
from captain.config import Config

log = logging.getLogger(__name__)


@cli.command(
    "build",
    short_help="Run the full build pipeline via mkosi.",
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
    "--mkosi-mode",
    envvar="MKOSI_MODE",
    default="docker",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="Mkosi stage execution mode (docker, native, skip).",
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
    "--iso-mode",
    envvar="ISO_MODE",
    default="docker",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="ISO build stage execution mode (docker, native, skip).",
)
@click.option(
    "--force",
    "force_mkosi",
    is_flag=True,
    default=False,
    help="Pass --force through to mkosi.",
)
@click.option(
    "--force-tools",
    envvar="FORCE_TOOLS",
    is_flag=True,
    default=False,
    help="Re-download tools even if outputs already exist.",
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
    mkosi_mode: str,
    tools_mode: str,
    iso_mode: str,
    force_mkosi: bool,
    force_tools: bool,
    force_iso: bool,
) -> None:
    """Run the full CaptainOS build pipeline.

    Stages executed in order: tools → initramfs (mkosi) → ISO → artifact
    collection.  Each stage can be independently set to run inside Docker,
    natively on the host, or skipped entirely.

    \b
    Examples
    --------
      captain build
      captain build --arch arm64
      captain build --flavor-id trixie-meson64 --arch arm64
      captain build --mkosi-mode native --tools-mode native
      captain build --force --force-tools
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
        mkosi_mode=mkosi_mode,
        iso_mode=iso_mode,
        force_tools=force_tools,
        force_iso=force_iso,
    )

    if force_mkosi:
        cfg.mkosi_args = ["--force"]

    # Instantiate and generate the flavor.
    flavor = captain.flavor.create_and_setup_flavor_for_id(cfg.flavor_id, cfg)
    flavor.generate()

    # Import build commands (reuse existing stage orchestration).
    from captain import artifacts
    from captain.cli._stages import (
        _build_iso_stage,
        _build_mkosi_stage,
        _build_tools_stage,
    )

    # Tools stage.
    _build_tools_stage(cfg)

    # Initramfs (mkosi) stage + artifact collection.
    _build_mkosi_stage(cfg, list(cfg.mkosi_args))
    artifacts.collect_initramfs(cfg)
    artifacts.collect_kernel(cfg)
    artifacts.collect_dtbs(cfg)
    log.info("Initramfs build complete.")

    # ISO stage (if the flavor supports it).
    if flavor.has_iso():
        _build_iso_stage(cfg)
    else:
        log.info("Flavor '%s' does not produce an ISO — skipping.", flavor.id)

    # Final artifact collection.
    artifacts.collect(cfg)
    log.info("Build complete!")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("captain").setLevel(level)
