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
@click.pass_obj
@click.pass_context
def shell_cmd(ctx: Context, cli_ctx: CliContext) -> None:
    log.warning("Running captainos in QEMU...")

    cfg = cli_ctx.make_config()

    extra_args: list[str] = ctx.args
    log.debug(f"Extra args passed to qemu: {extra_args}")

    run_qemu(cfg, extra_args)

    log.info("qemu exited.")
