"""Role traits: what the machine does once booted."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from captain.traits import Axis, Trait

if TYPE_CHECKING:
    from captain.flavor import Flavor


class Role(Trait):
    axis = Axis.ROLE
    # What the machine is, for humans: banner, motd, /etc/issue and /etc/os-release VARIANT=.
    title: ClassVar[str]
    # motd lines pointing at the role's logs and tools.
    hints: ClassVar[tuple[str, ...]] = ()
    # Module dirs (find -path patterns) the mem output drops: provisioning doesn't need them.
    trimmed_kernel_modules: ClassVar[tuple[str, ...]] = (
        # Filesystems not needed for provisioning
        "*/kernel/fs/btrfs",
        "*/kernel/fs/nfs",
        "*/kernel/fs/nfsd",
        "*/kernel/fs/ceph",
        "*/kernel/fs/ntfs3",
        # Network filesystems support (sunrpc is an NFS dependency)
        "*/kernel/net/sunrpc",
        "*/kernel/net/ceph",
        # Block devices
        "*/kernel/drivers/block/drbd",
        # Hypervisor / KVM
        "*/kernel/arch/x86/kvm",
        "*/kernel/virt",
        # Niche NIC driver
        "*/kernel/drivers/net/ethernet/netronome",
        # Sound stuff
        "*/kernel/sound",
        # Media stuff
        "*/kernel/drivers/media",
        # Wireless net drivers
        "*/kernel/drivers/net/wireless",
    )


class Tink(Role):
    """Tinkerbell provisioning: tink-agent pulled and run via containerd."""

    content = "role/tink"
    title = "Tinkerbell provisioning environment"
    hints = (
        "Use `journalctl -u tink-agent` command to access the tink worker/agent logs.",
        "Use `nerdctl` commands to access workflow action containers.",
    )

    def packages(self, flavor: Flavor) -> set[str]:
        # tink-agent-setup unpacks the image with tar (-z for OCI blobs);
        # Essential on Debian, not on Rocky.
        return {"tar", "gzip"}


class Kubernetes(Role):
    """Kubernetes node: kubeadm/kubelet/kubectl from pkgs.k8s.io, containerd (CRI), cloud-init."""

    content = "role/k8s"
    title = "Kubernetes node"
    hints = (
        "Use `journalctl -u kubelet` to access the kubelet logs.",
        "Use `crictl ps` / `crictl logs` to access pod containers.",
        "On control planes, use `kubectl --kubeconfig /etc/kubernetes/admin.conf`.",
    )
    # Workloads may need any of them (eg. NFS volumes)
    trimmed_kernel_modules = ()

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
            # cloud-init runs lsb_release on deb distros; resolute's cloud-init doesn't pull it in
            "lsb-release",
            # kubeadm preflight requirements
            "conntrack",
            "socat",
            "ebtables",
            "ethtool",
        }


class KubernetesCapt(Kubernetes):
    """Kubernetes node for Cluster API Provider Tinkerbell: cloud-init reads Tootles (EC2-style)."""

    content = "role/k8s-capt"
    title = "Kubernetes node (Cluster API Provider Tinkerbell)"
    hints = (
        "Use `cloud-init status --long` / `journalctl -u cloud-init` for the Tootles bootstrap.",
        *Kubernetes.hints,
    )

    @property
    def name(self) -> str:
        return "k8s-capt"


class KubernetesCaptTink(KubernetesCapt, Tink):
    """In-memory CAPT node: tink-agent runs the Workflow, which then releases cloud-init (kubeadm).

    Content along the MRO: tink, then k8s and k8s-capt over it (containerd keeps CRI), then ours.
    """

    content = "role/k8s-capt-tink"
    title = "Kubernetes node (Cluster API Provider Tinkerbell, in-memory)"
    hints = (
        "cloud-init is held back until the Workflow runs `captain-k8s-handoff`.",
        "Use `journalctl -u tink-agent` command to access the tink worker/agent logs.",
        *KubernetesCapt.hints,
    )

    @property
    def name(self) -> str:
        return "k8s-capt-tink"

    def custom_names(self) -> list[str]:
        return ["k8s-capt", self.name]

    def packages(self, flavor: Flavor) -> set[str]:
        # captain-state-disk: systemd-repart, formatting with mkfs.ext4; sshd once handed off
        extra = {"systemd-repart", "e2fsprogs", "openssh-server"}
        return KubernetesCapt.packages(self, flavor) | Tink.packages(self, flavor) | extra
