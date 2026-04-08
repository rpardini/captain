import logging
from dataclasses import dataclass
from pathlib import Path

from captain.config import Config
from captain.flavors.common_debian import DebianCommonFlavor

log: logging.Logger = logging.getLogger(__name__)


@dataclass
class TrixieACPIFlavor(DebianCommonFlavor):
    id = "trixie-acpi"
    name = "Trixie ACPI Common"
    description = "Debian Trixie based on UEFI+ACPI machines"
    supported_architectures = frozenset(["amd64", "arm64"])

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        super().setup(cfg, flavor_dir)

        this_flavor_dir = self.specific_flavor_dir("common-acpi")

        # Static files
        self.add_static_dir("mkosi.extra", this_flavor_dir)

    # This flavor can produce working ISO images (generic UEFI/ACPI)
    def has_iso(self) -> bool:
        return True
