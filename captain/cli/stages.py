"""Build stage orchestration — tools, mkosi, ISO."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from captain import docker, iso, kernel, tools
from captain.config import Config
from captain.util import check_kernel_dependencies, check_mkosi_dependencies, run

log = logging.getLogger(__name__)


def build_kernel_stage(cfg: Config) -> None:
    """Run the kernel build stage according to *cfg.kernel_mode*."""
    log.debug("Building kernel stage in mode %s", cfg.kernel_mode)

    # --- skip ---------------------------------------------------------
    if cfg.kernel_mode == "skip":
        log.info("KERNEL_MODE=skip — skipping kernel build")
        return

    # --- idempotency --------------------------------------------------
    image_deb_package = kernel.obtain_target_artifact_path(cfg)
    log.debug("Checking for existing kernel artifact at %s", image_deb_package)
    if image_deb_package.is_file() and not cfg.force_kernel:
        log.info("Kernel already built (use --force-kernel to rebuild)")
        return

    # Cleanup any existing outputs so that caches don't grow forever.
    if cfg.kernel_output.is_dir():
        shutil.rmtree(cfg.kernel_output)

    # --- native -------------------------------------------------------
    if cfg.kernel_mode == "native":
        missing = check_kernel_dependencies(cfg.arch)
        if missing:
            log.error("Missing kernel build tools: %s", ", ".join(missing))
            log.error("Install them or set --kernel-mode=docker.")
            raise SystemExit(1)
        log.info("Building kernel (native)...")
        kernel.build(cfg)
        return

    # --- docker -------------------------------------------------------
    docker.obtain_builder(cfg)
    log.info("Building kernel (docker relaunch)...")
    if cfg.kernel_menuconfig:
        log.info("Launching interactive kernel configuration (menuconfig)...")
        docker.run_captain_in_builder(cfg, ["kernel"], extra_docker_args=["-i", "-t"])
    else:
        docker.run_captain_in_builder(cfg, ["kernel"])
    docker.fix_docker_ownership(
        cfg,
        [
            f"/work/mkosi.input/kernel/{cfg.kernel_version}/{cfg.arch}",
            "/work/out",
        ],
    )


def _build_tools_stage(cfg: Config) -> None:
    """Run the tools download stage according to *cfg.tools_mode*."""
    log.debug("Building tools stage in mode %s", cfg.tools_mode)

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
    docker.obtain_builder(cfg)
    log.info("Downloading tools (nerdctl, containerd, etc.) docker...")
    docker.run_captain_in_builder(cfg, ["tools"])
    docker.fix_docker_ownership(cfg, ["/work/mkosi.input"])


def _build_mkosi_stage(cfg: Config, extra_args: list[str]) -> None:
    """Run the mkosi image-assembly stage according to *cfg.mkosi_mode*."""

    # --- skip ---------------------------------------------------------
    if cfg.mkosi_mode == "skip":
        log.info("MKOSI_MODE=skip — skipping image assembly")
        return

    # --- idempotency --------------------------------------------------
    initramfs_image = cfg.initramfs_output / "image.cpio.zst"
    force = "--force" in cfg.mkosi_args
    if initramfs_image.is_file() and not force:
        log.info("Initramfs already built: %s (use --force to rebuild)", initramfs_image)
        return

    mkosi_args = list(cfg.mkosi_args) + list(extra_args)

    # Use a Rich Syntax and Rich Panel to display mkosi.conf before running it if debugging:
    if log.isEnabledFor(logging.DEBUG):
        from rich import print
        from rich.panel import Panel
        from rich.syntax import Syntax

        mkosi_conf_path = cfg.project_dir / "mkosi.conf"
        if mkosi_conf_path.is_file():
            mkosi_conf_content = mkosi_conf_path.read_text()
            syntax = Syntax(
                mkosi_conf_content,
                "ini",
                theme="monokai",
                line_numbers=True,
                background_color="default",
            )
            panel = Panel(syntax, title="mkosi.conf", border_style="blue")
            print(panel)
        else:
            log.debug("No mkosi.conf found at %s", mkosi_conf_path)

    # --- native -------------------------------------------------------
    if cfg.mkosi_mode == "native":
        missing = check_mkosi_dependencies()
        if missing:
            log.error("Missing mkosi tools: %s", ", ".join(missing))
            log.error("Install them or set --mkosi-mode=docker.")
            raise SystemExit(1)
        log.info("Building initrd with mkosi (native)...")
        tools_tree = str(cfg.tools_output)
        output_dir = str(cfg.initramfs_output)
        run(
            [
                "mkosi",
                f"--architecture={cfg.arch_info.mkosi_arch}",
                f"--extra-tree={tools_tree}",
                f"--output-dir={output_dir}",
                "build",
                *mkosi_args,
            ],
            cwd=cfg.project_dir,
        )
        return

    # --- docker -------------------------------------------------------
    docker.obtain_builder(cfg)
    log.info("Building initrd with mkosi (docker)...")
    tools_tree = f"/work/mkosi.input/tools/{cfg.arch}"  # @TODO ooops
    output_dir = cfg.calc_initramfs_output(Path("/work"), "initramfs")
    docker.run_mkosi_in_builder(
        cfg,
        f"--extra-tree={tools_tree}",
        f"--output-dir={output_dir}",
        "--package-cache-dir=/cache/packages",
        "build",
        *mkosi_args,
    )
    docker.fix_docker_ownership(
        cfg,
        [
            f"/work/mkosi.output/initramfs/{cfg.flavor_id}/{cfg.arch}",
            "/work/out",
        ],
    )


def _build_iso_stage(cfg: Config) -> None:
    """Run the ISO build stage according to *cfg.iso_mode*."""

    # --- skip ---------------------------------------------------------
    if cfg.iso_mode == "skip":
        log.info("ISO_MODE=skip — skipping ISO build")
        return

    # --- idempotency --------------------------------------------------
    iso_path = cfg.iso_output / f"captainos-{cfg.flavor_id}-{cfg.arch_info.output_arch}.iso"
    if iso_path.is_file() and not cfg.force_iso:
        log.info("ISO already built: %s (use --force-iso to rebuild)", iso_path)
        return

    # --- native -------------------------------------------------------
    if cfg.iso_mode == "native":
        log.info("Building ISO (native)...")
        iso.build(cfg)
        return

    # --- docker -------------------------------------------------------
    docker.obtain_builder(cfg)
    log.info("Building ISO (docker)...")
    docker.run_captain_in_builder(cfg, ["iso"])
    docker.fix_docker_ownership(
        cfg,
        [
            "/work/mkosi.output/iso",
            "/work/out",
        ],
    )
