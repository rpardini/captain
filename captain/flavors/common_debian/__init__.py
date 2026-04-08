import logging
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
from captain.flavor import BaseFlavor

log: logging.Logger = logging.getLogger(__name__)


@dataclass
class DebianCommonFlavor(BaseFlavor):
    id = "common-debian"
    name = "Debian Common"
    description = "Base flavor for Debian-based distros"

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)

        this_flavor_dir = self.specific_flavor_dir("common-debian")

        # Templates
        self.template_map["mkosi.conf"] = [this_flavor_dir / "mkosi.conf.j2"]

        self.template_map["mkosi.postinst"] = [
            this_flavor_dir / "bash.header.sh",
            this_flavor_dir / "mkosi.postinst.sh.j2",
        ]

        self.template_map["mkosi.finalize"] = [
            this_flavor_dir / "bash.header.sh",
            this_flavor_dir / "mkosi.finalize.sh.j2",
        ]

        # Static files
        self.add_static_dir("mkosi.extra", this_flavor_dir)
        self.add_static_dir("mkosi.sandbox", this_flavor_dir)
        self.add_static_dir("mkosi.skeleton", this_flavor_dir)

    @abstractmethod
    def kernel_packages(self) -> set[str]:
        pass
