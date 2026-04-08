"""Build configuration populated from CLI args / environment variables."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from captain.util import ArchInfo, get_arch_info

log = logging.getLogger(__name__)

# Valid values for ISO_MODE and MKOSI_MODE.
VALID_MODES = ("docker", "native", "skip")

# The single source of truth for the default flavor.
# Override at runtime via --flavor-id or FLAVOR_ID env var.
DEFAULT_FLAVOR_ID = "trixie-full"


@dataclass(slots=True)
class Config:
    """All build configuration, loaded once from environment variables."""

    # Paths
    project_dir: Path
    output_dir: Path

    # Target
    arch: str = "amd64"
    flavor_id: str = DEFAULT_FLAVOR_ID

    # Docker
    builder_registry: str | None = None
    builder_repository: str | None = None
    builder_image: str = "captainos-builder"
    builder_push: bool = False

    # Per-stage mode: "docker" | "native" | "skip"
    tools_mode: str = "docker"
    mkosi_mode: str = "docker"
    iso_mode: str = "docker"
    release_mode: str = "docker"

    # Force flags
    force_tools: bool = False
    force_iso: bool = False

    # QEMU
    qemu_append: str = ""
    qemu_mem: str = "2G"
    qemu_smp: str = "2"

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
        return self.project_dir / "mkosi.output" / "tools" / self.arch

    @property
    def mkosi_output(self) -> Path:
        return self.project_dir / "mkosi.output"

    @property
    def initramfs_output(self) -> Path:
        """Per-version, per-arch directory for mkosi initramfs output."""
        return self.project_dir / "mkosi.output" / "initramfs" / self.flavor_id / self.arch

    @property
    def iso_output(self) -> Path:
        """Per-version, per-arch directory for the built ISO image."""
        return self.project_dir / "mkosi.output" / "iso" / self.flavor_id / self.arch

    @property
    def iso_staging(self) -> Path:
        """Per-version, per-arch staging directory for assembling the ISO filesystem."""
        return self.iso_output / "staging"
