"""Role traits: what the machine does once booted."""

from __future__ import annotations

from captain.traits import Axis, Trait


class Role(Trait):
    axis = Axis.ROLE


class Tink(Role):
    """Tinkerbell provisioning: tink-agent pulled and run via containerd."""

    content = "role/tink"
