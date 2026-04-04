import logging
from pathlib import Path

from captain.config import Config
from captain.flavor import BaseFlavor
from captain.flavors.common_debian import DebianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)

def create_flavor() -> BaseFlavor:
    return TrixieFullFlavor()


class TrixieFullFlavor(DebianCommonFlavor):
    def __init__(self) -> None:
        super().__init__()
        self.id = "trixie-full"
        self.name = "Trixie Full"
        self.description = "Debian Trixie based with linux-image-generic standard Debian kernel"
        self.supported_architectures = ["amd64", "arm64"]

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)
        log.warning(
            "TrixieFullFlavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )
