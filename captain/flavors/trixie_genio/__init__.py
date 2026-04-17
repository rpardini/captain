import logging
from dataclasses import dataclass

from captain.flavor import BaseFlavor
from captain.flavors.common_armbian import ArmbianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieGenioFlavor()


@dataclass
class TrixieGenioFlavor(ArmbianCommonFlavor):
    id = "trixie-genio"
    name = "Trixie for Mediatek Genio 64-bit ARM machines"
    description = "Debian Trixie with Armbian's genio-edge kernel"
    supported_architectures = frozenset(["arm64"])  # does NOT support amd64

    def flavor_packages(self) -> set[str]:
        return {"linux-image-edge-genio"}.union(super().flavor_packages())
