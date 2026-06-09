import logging
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
from captain.flavors.common_debian import DebianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


@dataclass
class ArmbianCommonFlavor(DebianCommonFlavor):
    id = "common-armbian"
    name = "Armbian Common"
    description = "Base flavor for Armbian-based distros"

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)

        this_flavor_dir = self.specific_flavor_dir("common-armbian")
        self.add_static_dir("mkosi.sandbox", this_flavor_dir)

    def has_iso(self) -> bool:
        return False

    def flavor_packages(self) -> set[str]:
        return {"tiny-initramfs"}.union(super().flavor_packages())

    def include_hwdb(self) -> bool:
        return True

    def include_working_apt(self) -> bool:
        return True
