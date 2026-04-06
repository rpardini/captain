import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_debian import DebianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieFullFlavor()


@dataclass
class TrixieFullFlavor(DebianCommonFlavor):
    id = "trixie-full"
    name = "Trixie Full"
    description = "Debian Trixie based with linux-image-generic standard Debian kernel"
    supported_architectures = frozenset(["amd64", "arm64"])

    def kernel_packages(self) -> set[str]:
        return {"linux-image-generic"}

    # This flavor can produce working ISO images (generic UEFI/ACPI)
    def has_iso(self) -> bool:
        return True
