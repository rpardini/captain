"""``captain tools`` — download tools (containerd, runc, nerdctl, CNI plugins)."""

from __future__ import annotations

import logging

import click
from click import Context

from captain.cli._main import CliContext, cli
from captain.qemu import run_qemu

log = logging.getLogger(__name__)


@cli.command(
    "qemu",
    context_settings={
        "ignore_unknown_options": True,
        "allow_extra_args": True,
    },
    short_help="Run the built captainos kernel+initramfs in QEMU.",
)
@click.option(
    "--mem",
    "qemu_mem",
    envvar="QEMU_MEM",
    default="2G",
    show_default=True,
    help="Guest memory (env: QEMU_MEM).",
)
@click.option(
    "--smp",
    "qemu_smp",
    envvar="QEMU_SMP",
    default="2",
    show_default=True,
    help="Guest CPUs (env: QEMU_SMP).",
)
@click.pass_obj
@click.pass_context
def shell_cmd(ctx: Context, cli_ctx: CliContext, qemu_mem: str, qemu_smp: str) -> None:
    log.debug("Running captainos in QEMU...")

    cfg = cli_ctx.make_config(qemu_mem=qemu_mem, qemu_smp=qemu_smp)

    extra_args: list[str] = ctx.args
    log.debug(f"Extra args passed to qemu: {extra_args}")

    run_qemu(cfg, extra_args)

    log.info("qemu exited.")
