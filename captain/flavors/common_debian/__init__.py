import logging
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
        log.warning(
            "DebianCommonFlavor setting up; mkosi arch: %s; flavor_dir: %s",
            cfg.arch_info.mkosi_arch,
            flavor_dir,
        )
        this_flavor_dir = self.specific_flavor_dir("common-debian")
        self.template_map["mkosi.conf"] = [this_flavor_dir / "mkosi.conf.j2"]
        self.template_map["mkosi.postinst"] = [this_flavor_dir / "bash.header.sh",
                                               this_flavor_dir / "mkosi.postinst.sh.j2"]
        self.template_map["mkosi.finalize"] = [this_flavor_dir / "bash.header.sh",
                                               this_flavor_dir / "mkosi.finalize.sh.j2"]

        # Now, lets enumerate and add all the static files this flavor's mkosi.extra directory
        # and add them to self.static_map with the key being the relative path from the flavor dir
        extra_dir = this_flavor_dir / "mkosi.extra"
        if extra_dir.exists() and extra_dir.is_dir():
            for extra_file in extra_dir.rglob("*"):
                if extra_file.is_file():
                    relative_path = extra_file.relative_to(this_flavor_dir)
                    self.static_map[str(relative_path)] = extra_file

        # Now, lets enumerate and add all the static files this flavor's mkosi.sandbox directory
        # and add them to self.static_map with the key being the relative path from the flavor dir
        extra_dir = this_flavor_dir / "mkosi.sandbox"
        if extra_dir.exists() and extra_dir.is_dir():
            for extra_file in extra_dir.rglob("*"):
                if extra_file.is_file():
                    relative_path = extra_file.relative_to(this_flavor_dir)
                    self.static_map[str(relative_path)] = extra_file

        # Now, lets enumerate and add all the static files this flavor's mkosi.skeleton directory
        # and add them to self.static_map with the key being the relative path from the flavor dir
        extra_dir = this_flavor_dir / "mkosi.skeleton"
        if extra_dir.exists() and extra_dir.is_dir():
            for extra_file in extra_dir.rglob("*"):
                if extra_file.is_file():
                    relative_path = extra_file.relative_to(this_flavor_dir)
                    self.static_map[str(relative_path)] = extra_file

    def extra_mkosi_conf_distribution(self) -> str:
        return ""
