"""Role traits: what the machine does once booted."""

from __future__ import annotations

from typing import TYPE_CHECKING

from captain.traits import Axis, Trait

if TYPE_CHECKING:
    from captain.flavor import Flavor


class Role(Trait):
    axis = Axis.ROLE


class Tink(Role):
    """Tinkerbell provisioning: tink-agent pulled and run via containerd."""

    content = "role/tink"

    def packages(self, flavor: Flavor) -> set[str]:
        # tink-agent-setup unpacks the image with tar (-z for OCI blobs);
        # Essential on Debian, not on Rocky.
        return {"tar", "gzip"}
