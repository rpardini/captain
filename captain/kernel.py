"""Kernel download, configuration, compilation, and packaging.

Heavy lifting (make) is still done via subprocess — only the
orchestration is in Python.  Called directly by ``cli.build_kernel_stage``
in both native and Docker modes (inside the container we re-enter
the CLI with all modes forced to native).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from captain import console
from captain.config import DEFAULT_KERNEL_VERSION, Config
from captain.util import ensure_dir, run, safe_extractall

KERNEL_BUILD_BASE_PATH = "/work/kernel-build"

RELEASES_JSON_URL = "https://www.kernel.org/releases.json"

log = logging.getLogger(__name__)

_DOWNLOAD_TIMEOUT = 60  # seconds


def _version_tuple(version: str) -> tuple[int, ...]:
    """Parse a dotted kernel version into an int tuple for comparison."""
    parts: list[int] = []
    for piece in version.split("."):
        # stop at the first non-numeric component (e.g. rc suffixes)
        if not piece.isdigit():
            break
        parts.append(int(piece))
    return tuple(parts)


def latest_branch_version(branch: str | None = None) -> str:
    """Return the newest kernel.org point release of *branch* (e.g. ``"6.18"``).

    Consults kernel.org's ``releases.json``, which lists the latest release of
    each active branch. *branch* defaults to the ``<major>.<minor>`` of
    :data:`DEFAULT_KERNEL_VERSION`. Falls back to ``DEFAULT_KERNEL_VERSION`` on
    any network/parse failure or when the branch is not listed — never returns
    an empty string, so callers/CI always get a buildable version.
    """
    if branch is None:
        branch = ".".join(DEFAULT_KERNEL_VERSION.split(".")[:2])

    try:
        req = urllib.request.Request(RELEASES_JSON_URL)
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        log.warning(
            "Could not fetch %s (%s); using default %s",
            RELEASES_JSON_URL,
            exc,
            DEFAULT_KERNEL_VERSION,
        )
        return DEFAULT_KERNEL_VERSION

    prefix = f"{branch}."
    matches = [
        r["version"]
        for r in data.get("releases", [])
        if isinstance(r.get("version"), str) and r["version"].startswith(prefix)
    ]
    if not matches:
        log.warning(
            "No kernel.org release for branch %s; using default %s", branch, DEFAULT_KERNEL_VERSION
        )
        return DEFAULT_KERNEL_VERSION

    latest = max(matches, key=_version_tuple)
    log.info("Latest kernel for branch %s is %s", branch, latest)
    return latest


def _download_with_progress(url: str, filename: Path) -> None:
    """Download *url* to *filename* with a Rich progress bar."""
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
        total = int(resp.headers.get("Content-Length", 0)) or None
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("    Downloading", total=total)
            with open(filename, "wb") as out:
                while True:
                    buf = resp.read(8192)
                    if not buf:
                        break
                    out.write(buf)
                    progress.update(task, advance=len(buf))


def download_kernel(cfg: Config, dest_dir: Path) -> Path:
    """Download and extract a kernel tarball.  Returns the source directory."""
    src_dir = dest_dir / f"linux-{cfg.kernel_version}"  # predict kernel tarball 1st-level dir name
    if src_dir.is_dir():
        log.info("Using cached kernel source at %s", src_dir)
        return src_dir

    major = cfg.kernel_version.split(".")[0]
    url = f"https://cdn.kernel.org/pub/linux/kernel/v{major}.x/linux-{cfg.kernel_version}.tar.xz"
    tarball = dest_dir / f"linux-{cfg.kernel_version}.tar.xz"

    log.info("Downloading kernel %s...", cfg.kernel_version)
    log.info("  URL: %s", url)
    ensure_dir(dest_dir)
    try:
        _download_with_progress(url, tarball)
    except urllib.error.HTTPError as exc:
        log.error("Download failed: %s — %s", exc, url)
        raise SystemExit(1) from None
    except urllib.error.URLError as exc:
        log.error("Download failed: %s — %s", exc.reason, url)
        raise SystemExit(1) from None

    log.info("Extracting kernel source...")
    with tarfile.open(tarball, "r:xz") as tf:
        safe_extractall(tf, path=dest_dir)
    tarball.unlink()

    return src_dir


def _kernel_branch(version: str) -> str:
    """Derive the stable branch prefix from a full kernel version."""
    parts = version.split(".")
    if len(parts) < 2:
        log.error("Invalid kernel version format: %s", version)
        raise SystemExit(1)
    return f"{parts[0]}.{parts[1]}.y"


def _find_defconfig(cfg: Config) -> Path:
    """Locate the defconfig for the current kernel version and architecture."""
    ai = cfg.arch_info
    branch = _kernel_branch(cfg.kernel_version)
    defconfig = cfg.project_dir / "kernel.configs" / f"{branch}.{ai.arch}"
    if defconfig.is_file():
        return defconfig

    configs_dir = cfg.project_dir / "kernel.configs"
    available = sorted(
        {
            p.name.rsplit(".", 1)[0]
            for p in configs_dir.glob(f"*.{ai.arch}")
            if not p.name.startswith(".")
        }
    )
    avail_str = ", ".join(available) if available else "(none)"
    log.error(
        "No kernel config found for %s on %s\n    Expected: %s\n    Available branches for %s: %s",
        branch,
        ai.arch,
        defconfig,
        ai.arch,
        avail_str,
    )
    raise SystemExit(1)


def configure_kernel(cfg: Config, src_dir: Path) -> None:
    """Apply defconfig and run olddefconfig."""
    ai = cfg.arch_info
    defconfig = _find_defconfig(cfg)

    make_env = {"ARCH": ai.kernel_arch}
    if ai.cross_compile:
        make_env["CROSS_COMPILE"] = ai.cross_compile

    log.info("Using defconfig: %s", defconfig)
    shutil.copy2(defconfig, src_dir / ".config")
    run(["make", "olddefconfig"], env=make_env, cwd=src_dir)

    log.debug(
        "Considering whether to launch menuconfig for manual config tweaks... %s",
        cfg.kernel_menuconfig,
    )

    if cfg.kernel_menuconfig:
        log.info("Launching menuconfig...")
        run(["make", "menuconfig"], env=make_env, cwd=src_dir)

        # run `make savedefconfig`
        log.info("Saving modified config...")
        run(["make", "savedefconfig"], env=make_env, cwd=src_dir)

        # copy the 'defconfig' back to the source - ready to commit
        shutil.copy(src_dir / "defconfig", defconfig)
        log.info("Updated defconfig saved to %s", defconfig)

        raise SystemExit(0)  # exit after menuconfig - no build

    branch = _kernel_branch(cfg.kernel_version)
    resolved = cfg.project_dir / "kernel.configs" / f".config.resolved.{branch}.{ai.arch}"
    shutil.copy2(src_dir / ".config", resolved)
    log.info("Resolved config saved to kernel.configs/.config.resolved.%s.%s", branch, ai.arch)

    if ai.kernel_arch == "x86_64":
        log.info("Increasing COMMAND_LINE_SIZE to 4096 (x86_64)...")
        setup_h = src_dir / "arch" / "x86" / "include" / "asm" / "setup.h"
        text = setup_h.read_text()
        new_text = re.sub(
            r"#define COMMAND_LINE_SIZE\s+2048",
            "#define COMMAND_LINE_SIZE 4096",
            text,
        )
        if new_text == text:
            log.warning(
                "COMMAND_LINE_SIZE patch did not match — the kernel default may have changed"
            )
        setup_h.write_text(new_text)


def build_kernel(cfg: Config, src_dir: Path) -> str:
    """Compile the kernel image and modules.  Returns the built kernel version string."""
    ai = cfg.arch_info
    nproc = os.cpu_count() or 1

    make_env = {"ARCH": ai.kernel_arch}
    if ai.cross_compile:
        make_env["CROSS_COMPILE"] = ai.cross_compile
        make_env["DPKG_DEB_COMPRESSOR_TYPE"] = "none"  # don't waste time compressing .deb

    if cfg.kernel_clean:
        log.info("Cleaning kernel...")
        run(
            ["make", f"-j{nproc}", "clean"],
            env=make_env,
            cwd=src_dir,
        )

    built_kver = run(
        ["make", "-s", "kernelrelease"],
        env={"ARCH": ai.kernel_arch},
        capture=True,
        cwd=src_dir,
    ).stdout.strip()

    log.info("Building kernel '%s' with %d jobs...", built_kver, nproc)
    run(
        ["make", f"-j{nproc}", "bindeb-pkg"],
        env=make_env,
        cwd=src_dir,
    )

    log.info("Built kernel version: %s", built_kver)
    return built_kver


def obtain_target_artifact_path(cfg, ensure_parent: bool = False) -> Path:
    if ensure_parent:
        ensure_dir(cfg.kernel_output)

    # let's hash:
    # 1) the input defconfig
    defconfig = _find_defconfig(cfg)
    hex_digest_defconfig = hashlib.sha256(defconfig.read_bytes()).hexdigest()
    # 2) the contents of this script (as an imperfect proxy for the build logic)
    script_path = Path(__file__)
    hex_digest_script = hashlib.sha256(script_path.read_bytes()).hexdigest()
    # Combine and shorten to 8 chars for the final version hash
    version_hash = hashlib.sha256((hex_digest_defconfig + hex_digest_script).encode()).hexdigest()
    version_hash_shorten = version_hash[:8]

    return (
        cfg.kernel_output / f"linux-image-{cfg.kernel_version}-captainos"
        f"_{cfg.kernel_version}-1-{version_hash_shorten}_"
        f"{cfg.arch_info.kernel_arch}.deb"
    )


def deploy_deb_to_output(cfg: Config, build_dir: Path, built_kver: str) -> None:
    # Find the newest file in build_dir matching linux-image-{built_kver}*.deb
    image_deb_package = build_dir.glob(f"linux-image-{built_kver}*.deb")
    image_deb_package = sorted(image_deb_package, key=lambda p: p.stat().st_mtime, reverse=True)
    if not image_deb_package:
        log.error("No linux-image-*.deb package found in %s", build_dir)
        raise SystemExit(1)
    image_deb_package = image_deb_package[0]
    log.info("Found built kernel package: %s", image_deb_package)

    # copy the deb package to the output directory
    target_deb_output = obtain_target_artifact_path(cfg, ensure_parent=True)
    log.debug("Copying built kernel package from %s to %s", image_deb_package, target_deb_output)
    shutil.copy2(image_deb_package, target_deb_output)

    # Show dpkg info for the copied package
    log.info("Kernel package info:")
    run(["dpkg", "-I", str(target_deb_output)])

    log.info("Kernel build complete:")
    log.info(
        "    linux-image:   %s (%.1fM)",
        target_deb_output,
        (target_deb_output.stat().st_size / (1024 * 1024)),
    )


def build(cfg: Config) -> None:
    """Full kernel build pipeline — download, configure, build, install."""
    if cfg.kernel_output.exists():
        shutil.rmtree(cfg.kernel_output)
    ensure_dir(cfg.kernel_output)

    log.info("Preparing kernel source...")
    # We've a 2-deep because make bindeb-pkg outputs to parent directory of source proper
    # Also because one can't share cache between architectures -- full rebuild everytime otherwise
    build_dir = Path(KERNEL_BUILD_BASE_PATH) / f"build-{cfg.arch_info.kernel_arch}"
    src_dir = download_kernel(cfg, build_dir)  # this is one down from build_dir

    log.debug("Kernel source directory: %s", src_dir)

    log.info("Configuring kernel...")
    configure_kernel(cfg, src_dir)

    log.info("Building kernel...")
    built_kver = build_kernel(cfg, src_dir)
    log.debug("Built kernel version: %s", built_kver)

    log.info("Installing kernel...")
    deploy_deb_to_output(cfg, build_dir, built_kver)
