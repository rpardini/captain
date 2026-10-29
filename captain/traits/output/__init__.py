"""Output traits: what mkosi produces (in-memory initramfs, disk image...)."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from captain.artifacts import OutputArchArtifact, OutputArchArtifactType
from captain.traits import Axis, Trait

if TYPE_CHECKING:
    from captain.flavor import Flavor


class Output(Trait):
    axis = Axis.OUTPUT
    supports_iso: ClassVar[bool] = False

    def kernel_initramfs_packages(self, flavor: Flavor) -> set[str]:
        """Packages providing the kernel's initramfs generator, for this output."""
        raise NotImplementedError


class Mem(Output):
    """In-memory: kernel + initramfs (cpio) holding the whole OS."""

    content = "output/mem"
    supports_iso = True

    def packages(self, flavor: Flavor) -> set[str]:
        # /init switch_root's from rootfs to a tmpfs before starting systemd
        return set(flavor.distro.switch_root_packages)

    def kernel_initramfs_packages(self, flavor: Flavor) -> set[str]:
        return flavor.distro.noop_initramfs_packages()

    def add_arch_artifacts(
        self, flavor: Flavor, output_arch: str, artifacts: list[OutputArchArtifact]
    ) -> None:
        flavor_id = flavor.cfg.flavor_id
        artifacts += [
            OutputArchArtifact(
                type=OutputArchArtifactType.FILE, name=f"vmlinuz-{flavor_id}-{output_arch}"
            ),
            OutputArchArtifact(
                type=OutputArchArtifactType.FILE, name=f"initramfs-{flavor_id}-{output_arch}"
            ),
        ]
        if flavor.has_iso():
            artifacts.append(
                OutputArchArtifact(
                    type=OutputArchArtifactType.FILE,
                    name=f"captainos-{flavor_id}-{output_arch}.iso",
                )
            )
        if output_arch == "aarch64" and flavor.platform.ships_dtbs:
            artifacts.append(
                OutputArchArtifact(
                    type=OutputArchArtifactType.DIRECTORY, name=f"dtb-{flavor_id}-{output_arch}"
                )
            )
