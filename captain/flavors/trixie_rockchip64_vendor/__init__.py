import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_armbian import ArmbianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieRockchip64VendorFlavor()


@dataclass
class TrixieRockchip64VendorFlavor(ArmbianCommonFlavor):
    id = "trixie-rockchip64-vendor"
    name = "Trixie for Rockchip 64-bit ARM machines - Rockchip Vendor Kernel"
    description = "Debian Trixie based with Armbian's rk35xx-vendor kernel"
    supported_architectures = frozenset(["arm64"])  # does NOT support amd64

    def kernel_packages(self) -> set[str]:
        return {"linux-image-vendor-rk35xx"}
