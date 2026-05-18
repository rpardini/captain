"""Build configuration populated from CLI args / environment variables."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from captain.util import ArchInfo, get_arch_info

log = logging.getLogger(__name__)

# Valid values for KERNEL_MODE and MKOSI_MODE.
VALID_MODES = ("docker", "native", "skip")

# The single source of truth for the default flavor.
# Override at runtime via --flavor-id or FLAVOR_ID env var.
DEFAULT_FLAVOR_ID = "trixie-full"

# Fallback for the default kernel version.
# The latest version can be obtained and passed as --kernel-version/KERNEL_VERSION
# via <@TODO cmd for listing from cached releases.json
# Override at runtime via --kernel-version or KERNEL_VERSION env var.
DEFAULT_KERNEL_VERSION = "6.18.34"


@dataclass(slots=True)
class Config:
    """All build configuration, loaded once from environment variables."""

    # Paths
    project_dir: Path

    # "across invocations" / "GHA interface dir"; project_dir / "out"
    output_dir: Path  # target of collect_xx() stuff, coming from mkosi.output

    # Target
    arch: str = "amd64"
    flavor_id: str = DEFAULT_FLAVOR_ID
    flavor_hash: str | None = None  # resolved at runtime

    # For kernel build
    build_kernel: bool = False
    kernel_version: str = DEFAULT_KERNEL_VERSION
    force_kernel: bool = False
    kernel_clean: bool = False
    kernel_menuconfig: bool = False

    # Docker
    builder_registry: str | None = None
    builder_repository: str | None = None
    builder_image: str = "captainos-builder"
    builder_push: bool = False
    verbose_docker: bool = False  # Pass --verbose to captain when re-launched in Docker

    # Per-stage mode: "docker" | "native" | "skip"
    tools_mode: str = "native"
    mkosi_mode: str = "docker"
    iso_mode: str = "docker"
    release_mode: str = "docker"
    kernel_mode: str = "docker"

    # Force flags
    force_tools: bool = False
    force_iso: bool = False
    force_release: bool = False

    # QEMU
    qemu_mem: str = "2G"
    qemu_smp: str = "2"

    # Release related
    release_registry: str | None = None
    release_repository: str | None = None
    release_oci_artifact_name: str | None = None
    release_target: str | None = None
    release_git_sha: str | None = None
    release_src_tag: str | None = None
    release_pull_output: Path | None = None
    release_new_tag: str | None = None

    # mkosi passthrough
    mkosi_args: list[str] = field(default_factory=list)

    # Derived (set in __post_init__)
    arch_info: ArchInfo = field(init=False)

    # Call uv (eg in Docker) using its own --verbose flag
    verbose_uv: bool = False

    def __post_init__(self) -> None:
        self.arch_info = get_arch_info(self.arch)
        self.arch = self.arch_info.arch  # normalise aliases (x86_64 → amd64, etc.)
        for name, value in (
            ("TOOLS_MODE", self.tools_mode),
            ("MKOSI_MODE", self.mkosi_mode),
            ("ISO_MODE", self.iso_mode),
            ("RELEASE_MODE", self.release_mode),
            ("KERNEL_MODE", self.kernel_mode),
        ):
            if value not in VALID_MODES:
                log.error("%s=%r is invalid. Valid values: %s", name, value, ", ".join(VALID_MODES))
                sys.exit(1)

    @property
    def tools_output(self) -> Path:
        """Per-arch staging directory for downloaded tools.

        Contains containerd, runc, nerdctl, and CNI plugins.
        Passed to mkosi via ``--extra-tree=`` to merge into the initramfs.
        Kernel modules are stored separately under :attr:`kernel_output`.
        """
        return self.project_dir / "mkosi.input" / "tools" / self.arch

    @property
    def kernel_output(self) -> Path:
        """Per-version, per-arch directory for all kernel build artifacts.

        Contains the vmlinuz image (loaded separately by iPXE) and
        a ``modules/`` subtree that mirrors a root filesystem layout
        (``usr/lib/modules/{kver}/``) so it can be passed directly
        as an ``--extra-tree=`` to mkosi.
        """
        return self.project_dir / "mkosi.input" / "kernel" / self.arch

    @property
    def initramfs_output(self) -> Path:
        """Per-version, per-arch directory for mkosi initramfs output."""
        base_dir: Path = self.project_dir
        return self.calc_initramfs_output(base_dir, "initramfs")

    @property
    def iso_output(self) -> Path:
        """Per-version, per-arch directory for the built ISO image."""
        base_dir: Path = self.project_dir
        return self.calc_initramfs_output(base_dir, "iso")

    def calc_initramfs_output(self, base_dir: Path, which: str) -> Path:
        log.debug("Asked for %s output dir; flavor_hash=%r", which, self.flavor_hash)
        # To know the output dir, we must know the flavor_hash; make sure.
        if self.flavor_hash is None:
            log.error("flavor_hash is not set; cannot determine initramfs output directory")
            raise ValueError("flavor_hash is not set; cannot determine initramfs output directory")

        flavor_id = (
            base_dir / "mkosi.output" / which / self.flavor_id / self.arch / self.flavor_hash
        )
        return flavor_id

    @property
    def iso_staging(self) -> Path:
        """Per-version, per-arch staging directory for assembling the ISO filesystem."""
        return self.iso_output / "staging"

    @property
    def custom_dir(self) -> Path:
        """Directory for custom user files"""
        return self.project_dir / "custom"
