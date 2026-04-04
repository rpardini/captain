import logging
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
from captain.flavor import BaseFlavor

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return DebianCommonFlavor()


@dataclass
class DebianCommonFlavor(BaseFlavor):
    id = "common-debian"
    name = "Debian Common"
    description = "Base flavor for Debian-based distros"

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)
        log.warning(
            "DebianCommonFlavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )
