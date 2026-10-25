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


class Kubernetes(Role):
    """Kubernetes node: kubeadm/kubelet/kubectl from pkgs.k8s.io, containerd (CRI), cloud-init."""

    content = "role/k8s"

    @property
    def name(self) -> str:
        return "k8s"

    def packages(self, flavor: Flavor) -> set[str]:
        return {
            "kubelet",
            "kubeadm",
            "kubectl",
            "cri-tools",
            "cloud-init",
            # kubeadm preflight requirements
            "conntrack",
            "socat",
            "ebtables",
            "ethtool",
        }


class KubernetesCapt(Kubernetes):
    """Kubernetes node for Cluster API Provider Tinkerbell: cloud-init reads Hegel (EC2-style)."""

    content = "role/k8s-capt"

    @property
    def name(self) -> str:
        return "k8s-capt"
