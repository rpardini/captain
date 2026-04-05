import logging
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
from captain.flavor import BaseFlavor
from captain.flavors.common_armbian import ArmbianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieRockchip64Flavor()


@dataclass
class TrixieRockchip64Flavor(ArmbianCommonFlavor):
    id = "trixie-rockchip64"
    name = "Trixie for Rockchip 64-bit ARM machines"
    description = "Debian Trixie based with Armbian's rockchip64-edge kernel"
    supported_architectures = frozenset(["arm64"])  # does NOT support amd64

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)
        log.warning(
            "TrixieRockchip64Flavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )

    def kernel_packages(self) -> set[str]:
        return {"linux-image-edge-rockchip64"}
