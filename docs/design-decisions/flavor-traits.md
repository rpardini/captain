# Flavors as Compositions of Traits

## Context

Flavors started as a single inheritance chain (`DebianCommonFlavor > TrixieACPIFlavor | ArmbianCommonFlavor >
trixie-*`), with one Python module directory per flavor and a single Debian-only `mkosi.conf.j2`. Every flavor was
implicitly the same kind of thing: an in-memory (initramfs) Debian image running tink-agent.

We want to vary more than "which kernel":

- **distro**: Debian Trixie, Ubuntu Resolute, Rocky Linux 10 (so `.deb` and `.rpm`)
- **platform**: UEFI/ACPI with the distro kernel, UEFI/ACPI with the CaptainOS kernel, DeviceTree with Armbian kernels
- **role**: tink-agent provisioning, or a Kubernetes node (kubeadm + cloud-init)
- **output**: in-memory (kernel + initramfs) or a disk image for final deployment

A single inheritance chain cannot express that product without duplicating whole flavors, and mixins over four axes
make the MRO hard to follow.

## Decision

A flavor is a composition of one **trait** per axis, and is declared in a single explicit registry
(`captain/flavors.py`):

```python
Flavor(
    id="trixie-rockchip64",
    distro=Debian("trixie"),
    platform=Armbian("linux-image-edge-rockchip64"),
    role=Tink(),
    output=Mem(),
)
```

Existing flavor IDs are unchanged and are implicitly `mem` + `tink`. New role/output combinations get explicit
prefixes, e.g. `mem-k8s-capt-trixie-full` and `img-k8s-capt-trixie-rockchip64`, where `capt` is the variant of the
`k8s` role.

### Traits

A trait (`captain/traits/__init__.py`) contributes:

- **packages**, as logical (Debian) names, which the distro maps to its own names (`iproute2` → `iproute` on Rocky);
- **content**: a directory with any of `mkosi.conf.j2`, `mkosi.postinst.sh.j2`, `mkosi.finalize.sh.j2`, `mkosi.extra/`,
  `mkosi.sandbox/`, `mkosi.skeleton/` and `mkosi.repart/`. Content is declared per class and collected along the MRO, so
  `Debian` gets `distro/` (generic `[Distribution]` settings) plus `distro/deb/` (apt bits). Inheritance is kept for
  "is a kind of" relationships within one axis (`ArmbianRpi(Armbian)`), never across axes.
- **hooks** (`pre_mkosi`, `post_mkosi`, `post_artifact_collect`), **artifacts**, and answers to flavor-wide questions
  (`keep_package_manager`, `keep_hwdb`, `cache_bust_token`).

Traits answer cross-axis questions by asking the flavor: a platform that uses the distro kernel asks
`flavor.distro.generic_kernel_packages()`, and asks `flavor.output.kernel_initramfs_packages()` for whatever satisfies
the kernel's initramfs-generator dependency (a no-op for in-memory outputs, the distro's real generator for disk images).

### mkosi drop-ins

Each content directory becomes one mkosi **drop-in directory** under the disposable `mkosi.generated/mkosi.conf.d/`,
numbered by axis (`10-core`, `20-distro`, `21-distro-deb`, `30-platform-acpi`, `40-role-tink`, `50-output-mem`, ...,
`90-custom`). mkosi merges these natively: list settings (`Packages=`, `RemoveFiles=`) append, later scalar settings
win, `mkosi.extra`/`mkosi.sandbox` trees overlay in order, and every drop-in's `mkosi.postinst`/`mkosi.finalize` runs in
order. mkosi is invoked with `--directory=mkosi.generated`.

Relative paths in a drop-in directory's config are resolved against that drop-in, so project paths are rendered via
`flavor.project_relative()` (`../../../<path>`), which works natively and in the builder container alike.

The user's `custom/` directory is always the last drop-in (`90-custom`).

### Outputs

- **`Mem`** (in-memory): `Format=cpio`; a custom `/init` switch_roots from rootfs to a tmpfs; the kernel's
  initramfs-generator dependency is satisfied as cheaply as possible (tiny-initramfs on Debian/Ubuntu).
- **`Img`** (disk image): `Format=disk` with our own `mkosi.repart/` definitions and `Bootable=no`: the img postinst
  generates the initrd with the distro's own generator (initramfs-tools on Debian, dracut on Ubuntu/Rocky,
  `--no-hostonly` as it runs in a container) and sets up either systemd-boot + a BLS entry in the ESP (`uefi` platforms)
  or `/boot/extlinux/extlinux.conf` (`extlinux` platforms). `SectorSize=512` is pinned: repart otherwise may format the
  ESP with 4K sectors, which UEFI firmware won't read on 512-byte-sector disks.

## Consequences

- Adding a flavor is one registry entry; adding a distro, platform, role or output is one trait.
- `generate()` produces a self-contained tree; the Docker builder mounts one directory instead of six paths.
- Each drop-in script carries its own copy of the bash `log` header, instead of one concatenated script.
