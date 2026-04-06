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

        # Now, lets enumerate and add all the static files this flavor's mkosi.sandbox directory
        # and add them to self.static_map with the key being the relative path from the flavor dir
        extra_dir = this_flavor_dir / "mkosi.sandbox"
        if extra_dir.exists() and extra_dir.is_dir():
            for extra_file in extra_dir.rglob("*"):
                if extra_file.is_file():
                    relative_path = extra_file.relative_to(this_flavor_dir)
                    self.static_map[str(relative_path)] = extra_file
