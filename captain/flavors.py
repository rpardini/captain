"""The flavor registry: every buildable flavor, composed from traits.

Existing IDs (e.g. ``trixie-full``) are implicitly in-memory + tink-agent.
"""

from __future__ import annotations

from captain.flavor import Flavor
from captain.traits.distro import Debian, Rocky, Ubuntu
from captain.traits.output import Mem
from captain.traits.platform import AcpiCaptainKernel, AcpiDistroKernel, Armbian
from captain.traits.platform.rpi import ArmbianRpi
from captain.traits.role import Tink

TRIXIE = Debian("trixie")
RESOLUTE = Ubuntu("resolute")
ROCKY10 = Rocky("10")

FLAVORS: list[Flavor] = [
    Flavor(
        id="trixie-full",
        name="Trixie Full",
        description="Debian Trixie based with linux-image-generic standard Debian kernel",
        distro=TRIXIE,
        platform=AcpiDistroKernel(),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-slim",
        name="Trixie Slim",
        description="Debian Trixie based with captainos slim kernel",
        distro=TRIXIE,
        platform=AcpiCaptainKernel(),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-armbian-rpi",
        name="Trixie for Raspberry Pi - Armbian bcm2711-current Kernel",
        description="Debian Trixie based on Armbian's bcm2711-current kernel",
        distro=TRIXIE,
        platform=ArmbianRpi(),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-genio",
        name="Trixie for Mediatek Genio 64-bit ARM machines",
        description="Debian Trixie with Armbian's genio-edge kernel",
        distro=TRIXIE,
        platform=Armbian("linux-image-edge-genio"),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-meson64",
        name="Trixie for Meson (Amlogic) 64-bit ARM machines",
        description="Debian Trixie based with Armbian's meson64-edge kernel",
        distro=TRIXIE,
        platform=Armbian("linux-image-edge-meson64"),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-rockchip64",
        name="Trixie for Rockchip 64-bit ARM machines",
        description="Debian Trixie based with Armbian's rockchip64-edge kernel",
        distro=TRIXIE,
        platform=Armbian("linux-image-edge-rockchip64"),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="trixie-rockchip64-vendor",
        name="Trixie for Rockchip 64-bit ARM machines - Rockchip Vendor Kernel",
        description="Debian Trixie based with Armbian's rk35xx-vendor kernel",
        distro=TRIXIE,
        platform=Armbian("linux-image-vendor-rk35xx"),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="rockylinux10-full",
        name="Rocky Linux 10 Full",
        description="Rocky Linux 10 (+EPEL) with the standard Rocky kernel",
        distro=ROCKY10,
        platform=AcpiDistroKernel(),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="resolute-full",
        name="Resolute Full",
        description="Ubuntu 26.04 Resolute with the standard linux-image-generic Ubuntu kernel",
        distro=RESOLUTE,
        platform=AcpiDistroKernel(),
        role=Tink(),
        output=Mem(),
    ),
    Flavor(
        id="resolute-rockchip64",
        name="Resolute for Rockchip 64-bit ARM machines",
        description="Ubuntu 26.04 Resolute with Armbian's rockchip64-edge kernel",
        distro=RESOLUTE,
        platform=Armbian("linux-image-edge-rockchip64"),
        role=Tink(),
        output=Mem(),
    ),
]
