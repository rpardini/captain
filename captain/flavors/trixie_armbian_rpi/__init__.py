import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_armbian import ArmbianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieArmbianRPiFlavor()


@dataclass
class TrixieArmbianRPiFlavor(ArmbianCommonFlavor):
    id = "trixie-armbian-rpi"
    name = "Trixie for Raspberry Pi - Armbian bcm2711-current Kernel"
    description = "Debian Trixie based on Armbian's rockchip64-edge kernel"
    supported_architectures = frozenset(["arm64"])  # does NOT support amd64

    def kernel_packages(self) -> set[str]:
        return {"linux-image-current-bcm2711"}
