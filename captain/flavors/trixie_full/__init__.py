import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_acpi import TrixieACPIFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieFullFlavor()


@dataclass
class TrixieFullFlavor(TrixieACPIFlavor):
    id = "trixie-full"
    name = "Trixie Full"
    description = "Debian Trixie based with linux-image-generic standard Debian kernel"
    supported_architectures = frozenset(["amd64", "arm64"])

    def flavor_packages(self) -> set[str]:
        pkgs = {
            "linux-image-generic",  # Debian's standard kernel (arm64/amd64)
            "tiny-initramfs",  # A tiny initramfs builder; required for kernel image
        }
        if self.include_working_apt():
            pkgs.add("apt")
        return pkgs.union(super().flavor_packages())

    def include_hwdb(self) -> bool:
        return True

    def include_working_apt(self) -> bool:
        return True
