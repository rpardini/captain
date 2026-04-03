"""Build and utility command handlers."""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

from captain import artifacts, docker, qemu
from captain.config import Config
from captain.util import run

from ._stages import (
    _build_iso_stage,
    _build_mkosi_stage,
    _build_tools_stage,
)

log = logging.getLogger(__name__)


def _cmd_tools(cfg: Config, _extra_args: list[str]) -> None:
    """Download tools (containerd, runc, nerdctl, CNI plugins)."""
    _build_tools_stage(cfg)
    log.info("Tools stage complete!")


def _cmd_initramfs(cfg: Config, extra_args: list[str]) -> None:
    """Build only the initramfs via mkosi, then collect artifacts."""
    _build_mkosi_stage(cfg, extra_args)
    artifacts.collect_initramfs(cfg)
    artifacts.collect_kernel(cfg)
    artifacts.collect_dtbs(cfg)
    log.info("Initramfs build complete!")


def _cmd_iso(cfg: Config, _extra_args: list[str]) -> None:
    """Build only the ISO image."""
    _build_iso_stage(cfg)
    artifacts.collect_iso(cfg)
    log.info("ISO build complete!")


def _cmd_build(cfg: Config, extra_args: list[str]) -> None:
    """Full build: tools → initramfs → iso → artifacts."""
    _build_tools_stage(cfg)
    _cmd_initramfs(cfg, extra_args)  # delegate, so it also collects
    _build_iso_stage(cfg)  # TODO also conditional... / and/or include dtb's for arm64
    artifacts.collect(cfg)
    log.info("Build complete!")


def _cmd_shell(cfg: Config, _extra_args: list[str]) -> None:
    """Interactive shell inside the builder container."""
    docker.build_builder(cfg)
    log.info("Entering builder shell (type 'exit' to leave)...")
    docker.run_in_builder(
        cfg,
        *(["-it"] if sys.stdout.isatty() and sys.stdin.isatty() else []),
        "--entrypoint",
        "/bin/bash",
        cfg.builder_image,
    )


def _cmd_clean(cfg: Config, _extra_args: list[str], args: object = None) -> None:
    """Remove build artifacts for the selected kernel version, or all."""
    clean_all = getattr(args, "clean_all", False)

    if clean_all:
        _clean_all(cfg)
    else:
        _clean_version(cfg)


def _clean_version(cfg: Config) -> None:
    """Remove build artifacts for a single kernel version."""
    kver = cfg.kernel_version
    log.info("Cleaning build artifacts for kernel %s (%s)...", kver, cfg.arch)
    mkosi_output = cfg.mkosi_output

    # Version-specific directories under mkosi.output/{stage}/{version}/{arch}
    version_dirs = [
        mkosi_output / "kernel" / kver / cfg.arch,
        mkosi_output / "initramfs" / kver / cfg.arch,
        mkosi_output / "iso" / kver / cfg.arch,
    ]

    has_docker = shutil.which("docker") is not None
    existing = [d for d in version_dirs if d.exists()]
    if existing and has_docker:
        # Use Docker to remove root-owned files from mkosi.
        # Invoke rm directly (no shell) to avoid injection via path components.
        container_path_args = [
            f"/work/mkosi.output/{d.relative_to(mkosi_output)}" for d in existing
        ]
        run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{cfg.project_dir}:/work",
                "-w",
                "/work",
                "debian:trixie",
                "rm",
                "-rf",
                "--",
                *container_path_args,
            ],
        )
    elif existing:
        for d in existing:
            shutil.rmtree(d, ignore_errors=True)

    # Remove versioned artifacts from out/
    if cfg.output_dir.exists():
        for pattern in (
            f"vmlinuz-{kver}-*",
            f"initramfs-{kver}-*",
            f"captainos-{kver}-*",
            f"sha256sums-{kver}-*",
        ):
            for p in cfg.output_dir.glob(pattern):
                p.unlink(missing_ok=True)

    log.info("Clean complete for kernel %s.", kver)


def _clean_all(cfg: Config) -> None:
    """Remove all build artifacts (all kernel versions)."""
    log.info("Cleaning ALL build artifacts...")
    mkosi_output = cfg.mkosi_output
    mkosi_cache = cfg.project_dir / "mkosi.cache"

    has_docker = shutil.which("docker") is not None
    if has_docker:
        # Use Docker to remove root-owned files from mkosi
        if mkosi_output.exists() or mkosi_cache.exists():
            run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{cfg.project_dir}:/work",
                    "-w",
                    "/work",
                    "debian:trixie",
                    "sh",
                    "-c",
                    "rm -rf /work/mkosi.output/image*"
                    " /work/mkosi.output/initramfs"
                    " /work/mkosi.output/kernel"
                    " /work/mkosi.output/tools"
                    " /work/mkosi.output/iso"
                    " /work/mkosi.cache",
                ],
            )
    else:
        # No Docker available — remove directly (may need sudo for root-owned mkosi files)
        for pattern in ("image*", "initramfs", "kernel", "tools", "iso"):
            for p in mkosi_output.glob(pattern):
                if p.is_dir():
                    shutil.rmtree(p, ignore_errors=True)
                else:
                    p.unlink(missing_ok=True)
        if mkosi_cache.exists():
            shutil.rmtree(mkosi_cache, ignore_errors=True)

    if cfg.output_dir.exists():
        shutil.rmtree(cfg.output_dir)
    log.info("Clean complete.")


def _cmd_summary(cfg: Config, _extra_args: list[str]) -> None:
    """Print mkosi configuration summary."""
    tools_tree = str(cfg.tools_output)
    output_dir = str(cfg.initramfs_output)
    match cfg.mkosi_mode:
        case "docker":
            docker.build_builder(cfg)
            container_tree = f"/work/mkosi.output/tools/{cfg.arch}"
            container_outdir = f"/work/mkosi.output/initramfs/{cfg.kernel_version}/{cfg.arch}"
            docker.run_mkosi(
                cfg,
                f"--extra-tree={container_tree}",
                f"--output-dir={container_outdir}",
                "summary",
            )
        case "native":
            run(
                [
                    "mkosi",
                    f"--architecture={cfg.arch_info.mkosi_arch}",
                    f"--extra-tree={tools_tree}",
                    f"--output-dir={output_dir}",
                    "summary",
                ],
                cwd=cfg.project_dir,
            )
        case "skip":
            log.error("Cannot show mkosi summary when MKOSI_MODE=skip.")
            raise SystemExit(1)


def _cmd_checksums(cfg: Config, _extra_args: list[str], args: object = None) -> None:
    """Compute SHA-256 checksums for the specified files."""
    files = getattr(args, "files", None) or []
    output = getattr(args, "output", None)

    if files:
        # Explicit mode: user provided specific files and output.
        if not output:
            log.error("--output is required when specifying files explicitly.")
            raise SystemExit(1)
        artifacts.collect_checksums(
            [Path(f) for f in files],
            Path(output),
        )
    else:
        # Default mode: produce checksums for the selected architecture.
        out = cfg.output_dir
        oarch = cfg.arch_info.output_arch
        kver = cfg.kernel_version
        arch_files = [
            out / f"vmlinuz-{kver}-{oarch}",
            out / f"initramfs-{kver}-{oarch}",
            out / f"captainos-{kver}-{oarch}.iso",
        ]
        existing = [f for f in arch_files if f.is_file()]
        if not existing:
            log.error("No artifacts found for %s-%s in %s", kver, oarch, out)
            raise SystemExit(1)
        dest = Path(output) if output else out / f"sha256sums-{kver}-{oarch}.txt"
        artifacts.collect_checksums(existing, dest)
    log.info("Checksums complete!")


def _cmd_qemu_test(cfg: Config, _extra_args: list[str], args: object = None) -> None:
    """Boot the image in QEMU for testing."""
    qemu.run_qemu(cfg, args=args)  # type: ignore[arg-type]
