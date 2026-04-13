"""``captain tools`` — download tools (containerd, runc, nerdctl, CNI plugins)."""

from __future__ import annotations

import logging

import click

from captain import artifacts, config
from captain.cli._main import CliContext, cli
from captain.cli._stages import _build_kernel_stage

log = logging.getLogger(__name__)


@cli.command(
    "kernel",
    short_help="Build Linux Kernel for CaptainOS trixie-slim flavor.",
)
@click.option(
    "--kernel-mode",
    envvar="KERNEL_MODE",
    default="docker",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="Kernel build stage execution mode (docker, native, skip).",
)
@click.option(
    "--force-kernel",
    envvar="FORCE_KERNEL",
    is_flag=True,
    default=False,
    help="Build kernel even if outputs already exist.",
)
@click.option(
    "--kernel-version",
    envvar="KERNEL_VERSION",
    default=config.DEFAULT_KERNEL_VERSION,
    show_default=True,
    help="Kernel version to build. Must match an official tarball.",
)
@click.pass_obj
def tools_cmd(
    cli_ctx: CliContext,
    *,
    kernel_mode: str,
    force_kernel: bool,
    kernel_version: str,
) -> None:
    log.warning("CLI kernel mode: %s", kernel_mode)

    cfg = cli_ctx.make_config(
        force_kernel=force_kernel,
        kernel_version=kernel_version,
        kernel_mode=kernel_mode,
        build_kernel=True,
    )

    _build_kernel_stage(cfg)
    artifacts.collect_kernel(cfg)
    log.info("Kernel build stage complete!")
