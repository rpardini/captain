import logging
from dataclasses import dataclass

from captain.artifacts import OutputArchArtifact
from captain.cli import stages
from captain.flavor import BaseFlavor
from captain.flavors.common_acpi import TrixieACPIFlavor
from captain.kernel import obtain_target_artifact_path

log: logging.Logger = logging.getLogger(__name__)


def create_flavor() -> BaseFlavor:
    return TrixieSlimFlavor()


@dataclass
class TrixieSlimFlavor(TrixieACPIFlavor):
    id = "trixie-slim"
    name = "Trixie Slim"
    description = "Debian Trixie based with captainos slim kernel"
    supported_architectures = frozenset(["amd64", "arm64"])

    def pre_mkosi_stage(self):
        log.debug("Flavor delegating to build_kernel_stage to ensure kernel .deb is present")
        # call the kernel build stage, to ensure kernel .deb is in mkosi.input/kernel/<arch>
        stages.build_kernel_stage(self.cfg)

    def flavor_packages(self) -> set[str]:
        return {f"linux-image-{self.cfg.kernel_version}-captainos"}.union(super().flavor_packages())

    def package_directories(self) -> set[str]:
        return {str(obtain_target_artifact_path(self.cfg).parent.relative_to(self.cfg.project_dir))}

    def add_arch_dtb_artifacts(self, artifacts: list[OutputArchArtifact], output_arch: str):
        # no dtb artifacts for trixie-slim flavor
        pass
