"""Build a UEFI-bootable live ISO from the vmlinuz + initramfs artifacts."""

from __future__ import annotations

import hashlib
import json
import logging
import mmap
import secrets
import shutil
import textwrap
from pathlib import Path

from captain.config import Config
from captain.util import ensure_dir, run

log = logging.getLogger(__name__)

# GRUB platform directory name per architecture.
_GRUB_PLATFORM = {
    "amd64": "x86_64-efi",
    "arm64": "arm64-efi",
}

# Console devices per architecture for the kernel cmdline.
_CONSOLE_ARGS = {
    "amd64": "console=tty0 console=ttyS0,115200",
    "arm64": "console=tty0 console=ttyAMA0,115200",
}

# Path of the bootstrap data slot inside the ISO filesystem. GRUB loads it as a
# second initrd so the kernel extracts it alongside the OS initramfs. Tinkerbell
# substitutes its bytes per host while serving the shared ISO, so its size is
# fixed at build time and never changes afterwards.
#
# Local to this build: Tinkerbell locates the slot by offset, not by name, so
# this only has to agree with the initrd line in _grub_cfg.
BOOTSTRAP_SLOT_ISO_PATH = "/boot/bootstrap.cpio"

# Reserved capacity of the slot. Raising it requires a new ISO release; changes
# that fit within it do not. Published in the layout rather than assumed by
# Tinkerbell, so it may differ per flavor.
BOOTSTRAP_SLOT_CAPACITY = 4 * 1024 * 1024

# The next two are the contract with Tinkerbell, along with the field names
# written by _write_bootstrap_layout. Tinkerbell treats a schema it does not
# know as an ISO with no slot, so bump the version only when the meaning of
# existing fields changes.
BOOTSTRAP_LAYOUT_VERSION = 1
BOOTSTRAP_LAYOUT_SUFFIX = ".layout.json"


def _grub_cfg(arch: str) -> str:
    """Generate the GRUB configuration for the ISO."""
    console = _CONSOLE_ARGS.get(arch, "console=tty0")
    return textwrap.dedent(f"""\
        set timeout=5
        set default=0

        menuentry "CaptainOS" {{
            linux /boot/vmlinuz {console} 464vn90e7rbj08xbwdjejmdf4it17c5zfzjyfhthbh19eij201hjgit021bmpdb9ctrc87x2ymc8e7icu4ffi15x1hah9iyaiz38ckyap8hwx2vt5rm44ixv4hau8iw718q5yd019um5dt2xpqqa2rjtdypzr5v1gun8un110hhwp8cex7pqrh2ivh0ynpm4zkkwc8wcn367zyethzy7q8hzudyeyzx3cgmxqbkh825gcak7kxzjbgjajwizryv7ec1xm2h0hh7pz29qmvtgfjj1vphpgq1zcbiiehv52wrjy9yq473d9t1rvryy6929nk435hfx55du3ih05kn5tju3vijreru1p6knc988d4gfdz28eragvryq5x8aibe5trxd0t6t7jwxkde34v6pj1khmp50k6qqj3nzgcfzabtgqkmeqhdedbvwf3byfdma4nkv3rcxugaj2d0ru30pa2fqadjqrtjnv8bu52xzxv7irbhyvygygxu1nt5z4fh9w1vwbdcmagep26d298zknykf2e88kumt59ab7nq79d8amnhhvbexgh48e8qc61vq2e9qkihzt1twk1ijfgw70nwizai15iqyted2dt9gfmf2gg7amzufre79hwqkddc1cd935ywacnkrnak6r7xzcz7zbmq3kt04u2hg1iuupid8rt4nyrju51e6uejb2ruu36g9aibmz3hnmvazptu8x5tyxk820g2cdpxjdij766bt2n3djur7v623a2v44juyfgz80ekgfb9hkibpxh3zgknw8a34t4jifhf116x15cei9hwch0fye3xyq0acuym8uhitu5evc4rag3ui0fny3qg4kju7zkfyy8hwh537urd5uixkzwu5bdvafz4jmv7imypj543xg5em8jk8cgk7c4504xdd5e4e71ihaumt6u5u2t1w7um92fepzae8p0vq93wdrd1756npu1pziiur1payc7kmdwyxg3hj5n4phxbc29x0tcddamjrwt260b0w
            initrd /boot/initramfs {BOOTSTRAP_SLOT_ISO_PATH}
        }}
    """)


def _newc_entry(ino: int, mode: int, nlink: int, name: str, data: bytes) -> bytes:
    """Serialize one `newc` (070701) CPIO record, padded to 4-byte alignment.

    Tinkerbell has its own serializer for the archives it writes into the slot.
    Both sides only have to emit valid `newc` for the kernel to extract; they
    exchange no values. The magic, the 110-byte header and the TRAILER!!! entry
    are fixed by the format.
    """
    fields = [ino, mode, 0, 0, nlink, 0, len(data), 0, 0, 0, 0, len(name) + 1, 0]
    out = b"070701" + b"".join(b"%08X" % f for f in fields) + name.encode() + b"\0"
    out += b"\0" * (-len(out) % 4)
    out += data
    out += b"\0" * (-len(out) % 4)
    return out


def _empty_cpio() -> bytes:
    """Return a valid, empty `newc` archive: nothing but the mandatory trailer."""
    return _newc_entry(0, 0, 1, "TRAILER!!!", b"")


def _stage_bootstrap_slot(boot_dir: Path) -> bytes:
    """Reserve the bootstrap slot and return the marker identifying it.

    The marker is unique per build so the slot can be located unambiguously in
    the finished ISO without parsing the ISO filesystem. It is overwritten once
    its offset has been recorded, so it never ships.
    """
    marker = b"CAPTAINOS-BOOTSTRAP-SLOT-v1:" + secrets.token_hex(16).encode()
    slot = boot_dir / Path(BOOTSTRAP_SLOT_ISO_PATH).name
    with slot.open("wb") as fh:
        fh.write(marker)
        fh.truncate(BOOTSTRAP_SLOT_CAPACITY)
    return marker


def _locate_bootstrap_slot(iso_path: Path, marker: bytes) -> int:
    """Return the absolute byte offset of the bootstrap slot within *iso_path*."""
    with iso_path.open("rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        offset = mm.find(marker)
        if offset < 0:
            log.error("Bootstrap slot marker not found in %s", iso_path)
            raise SystemExit(1)
        if mm.find(marker, offset + 1) >= 0:
            log.error("Bootstrap slot marker is not unique in %s", iso_path)
            raise SystemExit(1)
    if offset % 2048 != 0:
        log.error("Bootstrap slot at %d is not sector aligned in %s", offset, iso_path)
        raise SystemExit(1)
    if offset + BOOTSTRAP_SLOT_CAPACITY > iso_path.stat().st_size:
        log.error("Bootstrap slot at %d extends past the end of %s", offset, iso_path)
        raise SystemExit(1)
    return offset


def _finalize_bootstrap_slot(iso_path: Path, offset: int, marker: bytes) -> None:
    """Replace the marker with an empty archive so an unpatched ISO still boots."""
    payload = _empty_cpio()
    payload = payload.ljust(max(len(marker), len(payload)), b"\0")
    with iso_path.open("r+b") as fh:
        fh.seek(offset)
        fh.write(payload)


def _write_bootstrap_layout(iso_path: Path, offset: int) -> Path:
    """Publish the slot's location, bound to this exact ISO by size and digest."""
    digest = hashlib.sha256()
    with iso_path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)

    layout = {
        "version": BOOTSTRAP_LAYOUT_VERSION,
        "iso": {"size": iso_path.stat().st_size, "sha256": digest.hexdigest()},
        "slot": {
            "path": BOOTSTRAP_SLOT_ISO_PATH,
            "offset": offset,
            "capacity": BOOTSTRAP_SLOT_CAPACITY,
        },
    }
    layout_path = iso_path.with_name(iso_path.name + BOOTSTRAP_LAYOUT_SUFFIX)
    tmp_path = layout_path.with_name(layout_path.name + ".tmp")
    tmp_path.write_text(json.dumps(layout, indent=2) + "\n")
    tmp_path.replace(layout_path)
    return layout_path


def _find_vmlinuz(cfg: Config) -> Path:
    """Locate the vmlinuz kernel image."""
    vmlinuz_files = sorted(cfg.initramfs_output.glob("*.vmlinuz*"))
    if not vmlinuz_files:
        log.error("No vmlinuz found in %s", cfg.initramfs_output)
        raise SystemExit(1)
    return vmlinuz_files[0]


def _find_initramfs(cfg: Config) -> Path:
    """Locate the initramfs CPIO image."""
    cpio_files = sorted(cfg.initramfs_output.glob("*.cpio*"))
    if not cpio_files:
        log.error("No initramfs CPIO found in %s", cfg.initramfs_output)
        log.error("Build the initramfs first: ./build.py initramfs")
        raise SystemExit(1)
    return cpio_files[0]


def build(cfg: Config) -> None:
    """Build a UEFI-bootable ISO image for the configured architecture.

    The ISO layout is::

        iso/{version}/{arch}/staging/
        ├── boot/
        │   ├── grub/
        │   │   └── grub.cfg
        │   ├── vmlinuz
        │   ├── initramfs
        │   └── bootstrap.cpio

    ``grub-mkrescue`` turns this into a bootable ISO with an embedded
    EFI System Partition.

    ``bootstrap.cpio`` is a fixed-capacity, uncompressed CPIO archive loaded as
    a second initrd. Tinkerbell overwrites it in place while serving the ISO, so
    per-host data needs no ISO rebuild.
    """
    vmlinuz = _find_vmlinuz(cfg)
    initramfs = _find_initramfs(cfg)

    grub_platform = _GRUB_PLATFORM.get(cfg.arch)
    if grub_platform is None:
        log.error("Unsupported architecture for ISO build: %s", cfg.arch)
        raise SystemExit(1)

    staging = cfg.iso_staging
    if staging.exists():
        shutil.rmtree(staging)

    boot_dir = ensure_dir(staging / "boot")
    grub_dir = ensure_dir(boot_dir / "grub")

    log.info("Staging ISO filesystem at %s", staging)

    shutil.copy2(vmlinuz, boot_dir / "vmlinuz")
    shutil.copy2(initramfs, boot_dir / "initramfs")
    marker = _stage_bootstrap_slot(boot_dir)

    (grub_dir / "grub.cfg").write_text(_grub_cfg(cfg.arch))

    iso_dir = ensure_dir(cfg.iso_output)
    iso_path = iso_dir / f"captainos-{cfg.flavor_id}-{cfg.arch_info.output_arch}.iso"
    # The layout is written last, so its presence marks a complete ISO.
    iso_path.with_name(iso_path.name + BOOTSTRAP_LAYOUT_SUFFIX).unlink(missing_ok=True)

    log.info("Building ISO with grub-mkrescue (%s)...", grub_platform)
    grub_mkrescue = shutil.which("grub-mkrescue")
    if grub_mkrescue is None:
        log.error("grub-mkrescue not found. Install grub-common or use ISO_MODE=docker.")
        raise SystemExit(1)

    run(
        [
            grub_mkrescue,
            f"--directory=/usr/lib/grub/{grub_platform}",
            "-o",
            str(iso_path),
            str(staging),
        ]
    )

    size_mb = iso_path.stat().st_size / (1024 * 1024)
    log.info("ISO created: %s (%.1fM)", iso_path, size_mb)

    offset = _locate_bootstrap_slot(iso_path, marker)
    _finalize_bootstrap_slot(iso_path, offset, marker)
    layout_path = _write_bootstrap_layout(iso_path, offset)
    log.info(
        "Bootstrap slot %s reserved at offset %d (%d bytes); layout: %s",
        BOOTSTRAP_SLOT_ISO_PATH,
        offset,
        BOOTSTRAP_SLOT_CAPACITY,
        layout_path,
    )
