import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_armbian import ArmbianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieMeson64Flavor()


@dataclass
class TrixieMeson64Flavor(ArmbianCommonFlavor):
    id = "trixie-meson64"
    name = "Trixie for Meson (Amlogic) 64-bit ARM machines"
    description = "Debian Trixie based with Armbian's meson64-edge kernel"
    supported_architectures = frozenset(["arm64"])  # does NOT support amd64

    def flavor_packages(self) -> set[str]:
        return {"linux-image-edge-meson64"}.union(super().flavor_packages())
