"""Distro traits: distribution/release, package family, package-name mapping."""

from __future__ import annotations

from typing import ClassVar

from captain.traits import Axis, Trait


class Distro(Trait):
    axis = Axis.DISTRO
    content = "distro"
    family: ClassVar[str]
    mkosi_distribution: ClassVar[str]
    # Logical (Debian) package name -> this distro's name; None drops the package.
    package_map: ClassVar[dict[str, str | None]] = {}

    def __init__(self, release: str) -> None:
        self.release = release

    @property
    def name(self) -> str:
        return f"{self.mkosi_distribution}-{self.release}"

    def map_packages(self, packages: set[str]) -> set[str]:
        mapped = {self.package_map.get(p, p) for p in packages}
        return {p for p in mapped if p is not None}

    def generic_kernel_packages(self) -> set[str]:
        """The distro's standard, generic kernel."""
        raise NotImplementedError

    def noop_initramfs_packages(self) -> set[str]:
        """Whatever satisfies the kernel's initramfs-generator dependency, cheaply.

        Used for in-memory outputs, where the image itself is the initramfs.
        """
        raise NotImplementedError


class DebFamily(Distro):
    family = "deb"
    content = "distro/deb"

    def noop_initramfs_packages(self) -> set[str]:
        return {"tiny-initramfs"}


class Debian(DebFamily):
    mkosi_distribution = "debian"

    def generic_kernel_packages(self) -> set[str]:
        return {"linux-image-generic"}
