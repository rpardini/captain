"""Distro traits: distribution/release, package family, package-name mapping."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from captain.traits import Axis, Trait

if TYPE_CHECKING:
    from captain.flavor import Flavor


class Distro(Trait):
    axis = Axis.DISTRO
    content = "distro"
    family: ClassVar[str]
    mkosi_distribution: ClassVar[str]
    # Logical (Debian) package name -> this distro's name; None drops the package.
    package_map: ClassVar[dict[str, str | None]] = {}
    # Where the kernel package installs its DTBs, relative to the root (a single-match glob).
    kernel_dtb_glob: ClassVar[str]
    # ID_LIKE= for CaptainOS' own os-release (in-memory outputs).
    os_release_id_like: ClassVar[str]

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
    kernel_dtb_glob = "usr/lib/linux-image-*"

    def noop_initramfs_packages(self) -> set[str]:
        return {"tiny-initramfs"}


class Debian(DebFamily):
    mkosi_distribution = "debian"
    os_release_id_like = "debian"

    def generic_kernel_packages(self) -> set[str]:
        return {"linux-image-generic"}


class RpmFamily(Distro):
    family = "rpm"
    content = "distro/rpm"
    kernel_dtb_glob = "usr/lib/modules/*/dtb"
    package_map: ClassVar[dict[str, str | None]] = {
        "apt": "dnf",
        "dmsetup": "device-mapper",
        "iproute2": "iproute",
        "iptables": "iptables-nft",
        "iputils-ping": "iputils",
        "login": None,  # in util-linux
        "polkitd": "polkit",
        "procps": "procps-ng",
        "systemd-sysv": None,  # in systemd
        "udev": "systemd-udev",
    }

    def packages(self, flavor: Flavor) -> set[str]:
        # Debian's systemd ships networkd; RPM distros split it out.
        return {"systemd-networkd"}

    def noop_initramfs_packages(self) -> set[str]:
        # The kernel hard-requires dracut, which it gets anyway; nothing to add.
        return set()


class Rocky(RpmFamily):
    """Rocky Linux; needs EPEL (systemd-networkd, systemd-timesyncd, fastfetch, pv)."""

    content = "distro/rocky"
    mkosi_distribution = "rocky"
    os_release_id_like = "rocky rhel centos fedora"

    def packages(self, flavor: Flavor) -> set[str]:
        return super().packages(flavor) | {"rocky-release", "epel-release"}

    def generic_kernel_packages(self) -> set[str]:
        return {"kernel"}
