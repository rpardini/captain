import logging
from pathlib import Path

from captain.config import Config
from captain.flavor import BaseFlavor

log: logging.Logger = logging.getLogger(__name__)

def create_flavor() -> BaseFlavor:
    return DebianCommonFlavor()


class DebianCommonFlavor(BaseFlavor):
    def __init__(self) -> None:
        super().__init__()
        self.id = "common-debian"
        self.name = "Debian Common"
        self.description = "Base flavor for Debian-based distros; not meant to be used directly. Use as a parent class for specific Debian flavors (e.g. trixie-full)."
        self.supported_architectures = ["amd64", "arm64"]

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)
        log.warning(
            "DebianCommonFlavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )
