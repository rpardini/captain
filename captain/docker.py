"""Docker builder image management and container execution."""

from __future__ import annotations

import hashlib
import logging
import os
import platform
from pathlib import Path

from rich.table import Table

import captain
from captain.config import Config
from captain.kernel import KERNEL_BUILD_BASE_PATH
from captain.util import detect_current_machine_arch, run

log = logging.getLogger(__name__)


def _image_exists(image: str) -> bool:
    """Check if a Docker image exists locally."""
    result = run(
        ["docker", "image", "inspect", image],
        check=False,
        capture=True,
    )
    return result.returncode == 0


def _dockerfile_hash(cfg: Config) -> str:
    """Return the SHA-256 hex digest of the Dockerfile content.

    This is used as an image tag so that Dockerfile changes are detected
    automatically.
    """
    dockerfile = cfg.project_dir / "Dockerfile"
    local_arch = detect_current_machine_arch()
    hex_digest = hashlib.sha256(dockerfile.read_bytes()).hexdigest()
    return f"{local_arch}-{hex_digest}"


def obtain_builder(cfg: Config) -> None:
    """Build the Docker builder image when the Dockerfile has changed.

    The image is tagged with a content hash of the Dockerfile so that
    changes are detected even when the base image name stays the same.
    """
    tag = _dockerfile_hash(cfg)
    remote_tagged_image = f"{cfg.builder_registry}/{cfg.builder_repository}/builder:{tag}"
    local_tagged_image = f"{cfg.builder_image}:{tag}"

    log.debug(
        "Checking for existing builder image with tag '%s' or remote image '%s'",
        local_tagged_image,
        remote_tagged_image,
    )

    if _image_exists(local_tagged_image):
        log.info("Docker image '%s' is up to date with %s.", cfg.builder_image, local_tagged_image)
        # Ensure the un-hashed tag exists so later docker-run calls that
        # reference cfg.builder_image (without the hash suffix) succeed.
        run(["docker", "tag", local_tagged_image, cfg.builder_image], check=False)
        return

    # Check if the remote name exists locally... (was pre-pulled somehow)
    if _image_exists(remote_tagged_image):
        log.info(
            "Docker image '%s' already exists locally (pre-pulled). Tagging as '%s'.",
            remote_tagged_image,
            cfg.builder_image,
        )
        run(["docker", "tag", remote_tagged_image, cfg.builder_image], check=False)
        return

    # Check if we can pull the remote image (exists in registry and matches our Dockerfile hash)
    if (
        run(
            ["docker", "pull", remote_tagged_image],
            check=False,
            capture=False,
        ).returncode
        == 0
    ):
        log.info(
            "Pulled Docker image '%s' from registry. Tagging as '%s'.",
            remote_tagged_image,
            cfg.builder_image,
        )
        run(["docker", "tag", remote_tagged_image, cfg.builder_image], check=False)
        return

    # build locally if no existing image was found.
    log.info("Building Docker image '%s'...", cfg.builder_image)
    run(
        [
            "docker",
            "buildx",
            "build",
            "--load",  # for older Docker versions
            "--progress=plain",
            "-t",
            local_tagged_image,
            "-t",
            cfg.builder_image,
            str(cfg.project_dir),
        ]
    )

    # Show the layer size distribution for the built image to help with debugging and optimization.
    log.info("Docker image '%s' built successfully. Layer size distribution:", local_tagged_image)
    layer_sizes_lines = run(
        [
            "docker",
            "history",
            "--no-trunc",
            "--format",
            "-> {{.Size}} :: '{{.CreatedBy}}'",
            local_tagged_image,
        ],
        capture=True,
        check=True,
    )
    layers = []
    for line in layer_sizes_lines.stdout.strip().splitlines():
        line = line.strip()
        if line.startswith("-> "):
            # remove double whitespace chars to make it easier to read
            line = " ".join(line.split())
            layers.append(line)
    # reverse the array to match the order
    layers.reverse()
    for layer in layers:
        log.info("Layer info: %s", layer)

    # Optionally push the image after building it
    if cfg.builder_push:
        log.info(
            "Pushing Docker image '%s' to registry as '%s'...",
            cfg.builder_image,
            remote_tagged_image,
        )
        run(["docker", "tag", local_tagged_image, remote_tagged_image], check=False)
        run(["docker", "push", remote_tagged_image])


def run_in_builder(
    cfg: Config, command_and_args: list[str], extra_docker_args: list[str] | None = None
) -> None:
    """Run a command inside the Docker builder container.

    *extra_args* are appended after the docker run flags and image name.
    """

    docker_envs: dict[str, str] = {
        "CAPTAIN_IN_DOCKER": "docker",
        "ARCH": cfg.arch,
        "FLAVOR_ID": cfg.flavor_id,
        "KERNEL_VERSION": cfg.kernel_version,
        "FORCE_TOOLS": str(int(cfg.force_tools)),
        "FORCE_ISO": str(int(cfg.force_iso)),
        "FORCE_KERNEL": f"{int(cfg.force_kernel)!s}",
        "BUILDAH_ISOLATION": "chroot",
        "BUILDAH_INSECURE": os.environ.get("BUILDAH_INSECURE", ""),
        "KERNEL_MODE": "native",
        "RELEASE_MODE": "native",
        "TOOLS_MODE": "native",
        "MKOSI_MODE": "native",
        "ISO_MODE": "native",
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "FORCE_COLOR": "1",
        "COLUMNS": str(captain.env_columns),
        "GITHUB_ACTIONS": os.environ.get("GITHUB_ACTIONS", ""),
        # Forward host registry credentials so buildah/skopeo can authenticate.
        # The caller sets these env vars on the host (e.g. via docker login or
        # CI secrets); they are passed through to the container as-is.
        "REGISTRY_AUTH_FILE": os.environ.get("REGISTRY_AUTH_FILE", ""),
        "REGISTRY_USERNAME": os.environ.get("REGISTRY_USERNAME", ""),
        "REGISTRY_PASSWORD": os.environ.get("REGISTRY_PASSWORD", ""),
        "CAPTAIN_VERBOSE": "1" if cfg.verbose_docker else "0",
        "CONFIG_KERNEL": "1" if cfg.kernel_menuconfig else "0",
    }

    docker_args: list[str] = [
        "docker",
        "run",
        "--rm",
        "--privileged",  # yes, this is required for both buildah and mkosi in the container
        "-w",
        "/work",
    ]

    if extra_docker_args is not None:
        log.debug("Adding extra Docker args: %s", extra_docker_args)
        docker_args.extend(extra_docker_args)

    if log.isEnabledFor(logging.DEBUG):
        table = Table(
            title="Docker Environment Variables", show_header=True, header_style="bold cyan"
        )
        table.add_column("Environment Variable", style="green")
        table.add_column("Value", style="yellow")
        for key, value in sorted(docker_envs.items()):
            table.add_row(key, value)
        captain.console.print(table)

    for k, v in docker_envs.items():
        docker_args += ["-e", f"{k}={v}"]

    docker_args += ["-v", f"{cfg.project_dir}/kernel.configs:/work/kernel.configs"]
    docker_args += ["-v", f"{cfg.project_dir}/mkosi.output:/work/mkosi.output"]
    docker_args += ["-v", f"{cfg.project_dir}/out:/work/out"]

    docker_args += ["-v", f"{cfg.project_dir}/mkosi.extra:/work/mkosi.extra"]
    docker_args += ["-v", f"{cfg.project_dir}/mkosi.sandbox:/work/mkosi.sandbox"]
    docker_args += ["-v", f"{cfg.project_dir}/mkosi.skeleton:/work/mkosi.skeleton"]

    docker_args += ["-v", f"{cfg.project_dir}/mkosi.conf:/work/mkosi.conf"]
    docker_args += ["-v", f"{cfg.project_dir}/mkosi.finalize:/work/mkosi.finalize"]
    docker_args += ["-v", f"{cfg.project_dir}/mkosi.postinst:/work/mkosi.postinst"]

    docker_args += ["-v", f"{cfg.project_dir}/captain:/work/captain"]
    docker_args += ["-v", f"{cfg.project_dir}/pyproject.toml:/work/pyproject.toml"]
    docker_args += ["-v", f"{cfg.project_dir}/build.py:/work/build.py"]

    docker_args += ["--mount", "type=volume,source=captain-cache-packages,target=/cache/packages"]
    docker_args += [
        "--mount",
        f"type=volume,source=captain-kernel-build,target={KERNEL_BUILD_BASE_PATH}",
    ]
    docker_args += [cfg.builder_image]

    docker_args.extend(command_and_args)
    run(docker_args)


def run_captain_in_builder(
    cfg: Config, command_and_args: list[str], extra_docker_args: list[str] | None = None
):
    log.debug("Running 'captain %s' in builder container...", command_and_args)
    run_in_builder(
        cfg,
        [
            "/usr/bin/uv",
            *(["--verbose"] if cfg.verbose_uv else ["--quiet"]),
            "run",
            "captain",
            *command_and_args,
        ],
        extra_docker_args=extra_docker_args,
    )


def run_mkosi_in_builder(cfg: Config, *mkosi_args: str) -> None:
    """Run mkosi inside the builder container."""
    ensure_binfmt(cfg)
    run_in_builder(
        cfg,
        command_and_args=[
            "/usr/local/bin/mkosi",
            f"--architecture={cfg.arch_info.mkosi_arch}",
            *mkosi_args,
        ],
    )


def ensure_binfmt(cfg: Config) -> None:
    """Register binfmt_misc handlers if doing a cross-architecture build."""
    host_arch = platform.machine()
    need_binfmt = False

    match (host_arch, cfg.arch):
        case ("x86_64", "arm64" | "aarch64"):
            need_binfmt = True
        case ("aarch64", "amd64" | "x86_64"):
            need_binfmt = True

    if not need_binfmt:
        return

    log.info(
        "Registering binfmt_misc handlers for cross-arch build (%s -> %s)...",
        host_arch,
        cfg.arch,
    )
    result = run(
        [
            "docker",
            "run",
            "--rm",
            "--privileged",
            "tonistiigi/binfmt",
            "--install",
            "all",
        ],
        check=False,
        capture=True,
    )
    if result.returncode != 0:
        log.warning("Could not auto-register binfmt handlers.")
        log.warning("Run manually: docker run --privileged --rm tonistiigi/binfmt --install all")


def fix_docker_ownership(cfg: Config, paths: list[str]) -> None:
    """Fix ownership of Docker-created files (container runs as root).

    Spawns a lightweight container to ``chown -R`` the given paths
    back to the calling user so that subsequent native-mode stages
    and the host user can read/write them.

    Idempotent: skips the chown if every path either does not exist
    or is already owned by the current user.
    """
    uid = os.getuid()
    gid = os.getgid()

    needs_fix: list[str] = []
    for p in paths:
        host_path = Path(p.replace("/work", str(cfg.project_dir), 1))
        if not host_path.exists():
            continue
        check_paths = [host_path]
        if host_path.is_dir():
            check_paths.extend(host_path.rglob("*"))
        for cp in check_paths:
            try:
                st = cp.stat()
            except OSError:
                continue
            if st.st_uid != uid or st.st_gid != gid:
                needs_fix.append(p)
                break

    if not needs_fix:
        return

    log.info("Fixing ownership of Docker-created files...")
    run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{cfg.project_dir}:/work",
            "-w",
            "/work",
            "debian:trixie",
            "chown",
            "-R",
            f"{uid}:{gid}",
            *needs_fix,
        ],
    )
