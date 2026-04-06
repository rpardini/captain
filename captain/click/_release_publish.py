"""``captain release-publish`` — publish artifacts as OCI images via buildah."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import captain.flavor
import click
from captain import oci
from captain.click._main import cli, common_options, resolve_project_dir
from captain.config import Config
from captain.util import check_release_dependencies

log = logging.getLogger(__name__)


@cli.command(
    "release-publish",
    short_help="Publish build artifacts as a multi-arch OCI image.",
)
@common_options
@click.option(
    "--builder-image",
    envvar="BUILDER_IMAGE",
    default="captainos-builder",
    show_default=True,
    help="Docker builder image name.",
)
@click.option(
    "--no-cache",
    envvar="NO_CACHE",
    is_flag=True,
    default=False,
    help="Rebuild images without Docker layer cache.",
)
@click.option(
    "--release-mode",
    envvar="RELEASE_MODE",
    default="native",
    show_default=True,
    type=click.Choice(["docker", "native", "skip"], case_sensitive=False),
    metavar="MODE",
    help="Release stage execution mode (docker, native, skip).",
)
@click.option(
    "--registry",
    envvar="REGISTRY",
    default="ghcr.io",
    show_default=True,
    help="OCI registry hostname.",
)
@click.option(
    "--repository",
    envvar="GITHUB_REPOSITORY",
    default="tinkerbell/captain",
    show_default=True,
    help="Repository path (owner/name).",
)
@click.option(
    "--oci-artifact-name",
    envvar="OCI_ARTIFACT_NAME",
    default="artifacts",
    show_default=True,
    help="OCI artifact image name.",
)
@click.option(
    "--target",
    envvar="TARGET",
    default=None,
    type=click.Choice(["amd64", "arm64", "combined"], case_sensitive=False),
    metavar="TARGET",
    help="Artifact target: amd64, arm64, or combined (default: value of --arch); "
    "combined requires trixie-full or equivalent flavor with both architectures' outputs present.",
)
@click.option(
    "--git-sha",
    envvar="GITHUB_SHA",
    default=None,
    help="Git commit SHA (default: auto-detected via git rev-parse HEAD).",
)
@click.option(
    "--version-exclude",
    envvar="VERSION_EXCLUDE",
    default=None,
    help="Tag to exclude from git-describe version lookup.",
)
@click.option(
    "--force",
    "force",
    is_flag=True,
    default=False,
    help="Publish even if the image already exists in the registry.",
)
def release_publish_cmd(
    *,
    arch: str,
    flavor_id: str,
    project_dir: str | None,
    verbose: bool,
    builder_image: str,
    no_cache: bool,
    release_mode: str,
    registry: str,
    repository: str,
    oci_artifact_name: str,
    target: str | None,
    git_sha: str | None,
    version_exclude: str | None,
    force: bool,
) -> None:
    """Publish build artifacts as a multi-arch OCI image to a registry.

    Uses buildah to construct OCI images from the build artifacts (kernel,
    initramfs, ISO, DTBs) and pushes them to the specified registry.

    Each artifact file becomes its own layer.  Deterministic tar generation
    ensures byte-identical layers across runs so that registries can
    deduplicate blobs.

    \b
    Examples
    --------
      captain release-publish
      captain release-publish --arch arm64 --target arm64
      captain release-publish --target combined --force
      captain release-publish --registry ghcr.io --repository tinkerbell/captain
    """
    _configure_logging(verbose)

    proj = resolve_project_dir(project_dir)

    if target is None:
        target = arch

    cfg = Config(
        project_dir=proj,
        output_dir=proj / "out",
        arch=arch,
        flavor_id=flavor_id,
        builder_image=builder_image,
        no_cache=no_cache,
        release_mode=release_mode,
    )

    # --- skip mode --------------------------------------------------------
    if cfg.release_mode == "skip":
        log.info("RELEASE_MODE=skip — nothing to do.")
        return

    # --- docker mode ------------------------------------------------------
    if cfg.release_mode == "docker":
        from captain import docker

        docker.build_release_image(cfg)
        sha = _resolve_git_sha(git_sha, proj)

        env_args: list[str] = [
            "-e",
            f"FLAVOR_ID={cfg.flavor_id}",
            "-e",
            f"REGISTRY={registry}",
            "-e",
            f"GITHUB_REPOSITORY={repository}",
            "-e",
            f"OCI_ARTIFACT_NAME={oci_artifact_name}",
            "-e",
            f"GITHUB_SHA={sha}",
            "-e",
            f"TARGET={target}",
        ]
        if version_exclude:
            env_args += ["-e", f"VERSION_EXCLUDE={version_exclude}"]
        if force:
            env_args += ["-e", "FORCE=true"]

        inner_cmd = ["/work/build.py", "release", "publish"]

        try:
            docker.run_in_release(
                cfg,
                *env_args,
                "--entrypoint",
                "/usr/bin/uv",
                docker.RELEASE_IMAGE,
                *(["--verbose"] if log.isEnabledFor(logging.DEBUG) else []),
                "run",
                *inner_cmd,
            )
        except subprocess.CalledProcessError as exc:
            raise SystemExit(exc.returncode) from None
        docker.fix_docker_ownership(cfg, ["/work/out"])
        return

    # --- native mode ------------------------------------------------------
    missing = check_release_dependencies()
    if missing:
        log.error("Missing release tools: %s", ", ".join(missing))
        log.error("Install them or set --release-mode=docker.")
        raise SystemExit(1)

    sha = _resolve_git_sha(git_sha, proj)
    tag = oci.compute_version_tag(proj, sha, exclude=version_exclude)
    tag = f"{tag}-{cfg.flavor_id}"

    flavor = captain.flavor.create_and_setup_flavor_for_id(cfg.flavor_id, cfg)

    oci.publish(
        cfg,
        flavor,
        target=target,
        registry=registry,
        repository=repository,
        artifact_name=oci_artifact_name,
        tag=tag,
        sha=sha,
        force=force,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_git_sha(sha: str | None, project_dir: Path) -> str:
    """Return the provided SHA or auto-detect via ``git rev-parse HEAD``."""
    if sha:
        return sha
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
        cwd=project_dir,
    )
    return result.stdout.strip()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.getLogger("captain").setLevel(level)
