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

        # Allow for easily user-customizable dirs and scripts
        # those apply to all flavors that inherit from this common-debian base.
        # Use-cases:
        #  - add CA root certificate to global trust store (via ca-certificates package)
        #  - add some Debian package (eg firmware) - [handled in flavor_packages() below]
        #  - configure containerd to use specific mirrors
        #  - run some postinst or finalize script to do some custom configuration
        self.add_static_dir("files", cfg.custom_dir, "mkosi.extra")
        self.add_custom_scripts(cfg, "mkosi-postinst", "mkosi.postinst")
        self.add_custom_scripts(cfg, "mkosi-finalize", "mkosi.finalize")

    def add_custom_scripts(self, cfg: Config, in_dir: str, out_script: str):
        custom_postinst_dir = cfg.custom_dir / in_dir
        if custom_postinst_dir.exists() and custom_postinst_dir.is_dir():
            files_in_order = sorted(custom_postinst_dir.iterdir())
            log.debug(
                "Adding custom %s scripts from %s: %s",
                out_script,
                custom_postinst_dir,
                files_in_order,
            )
            for file in files_in_order:
                if file.is_file():
                    log.debug("Adding custom %s script: %s", out_script, file)
                    self.template_map[out_script].append(file)

    @abstractmethod
    def flavor_packages(self) -> set[str]:
        packages = set({})
        # look into cfg.custom_dir/packages.txt, if it exists, read each non-comment line
        custom_packages_file = self.cfg.custom_dir / "packages.txt"
        if custom_packages_file.exists():
            log.debug("Reading custom packages from %s", custom_packages_file)
            packages = set(
                {
                    line.strip()
                    for line in (custom_packages_file.read_text().splitlines())
                    if line.strip() and not line.strip().startswith("#")
                }
            )
        return packages

    def sorted_flavor_packages(self) -> list[str]:
        return sorted(self.flavor_packages())

    def package_directories(self) -> set[str]:
        return set({})

    def include_working_apt(self) -> bool:
        return False

    def include_hwdb(self) -> bool:
        return False
