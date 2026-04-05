import logging
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
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

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)
        log.warning(
            "TrixieFullFlavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )
