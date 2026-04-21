"""``captain release-publish`` — publish artifacts as OCI images via buildah."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import click

import captain.flavor
from captain import oci
from captain.cli._main import CliContext, cli
from captain.util import check_release_dependencies

log = logging.getLogger(__name__)


@cli.command(
    "release-publish",
    short_help="Publish build artifacts as a multi-arch OCI image.",
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
    "combined requires trixie-full or equivalent flavor with both arch's outputs present.",
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
@click.pass_obj
def release_publish_cmd(
    cli_ctx: CliContext,
    *,
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

    if target is None:
        target = cli_ctx.arch
    assert isinstance(target, str)

    cfg = cli_ctx.make_config(release_mode=release_mode)

    # --- skip mode --------------------------------------------------------
    if cfg.release_mode == "skip":
        log.info("RELEASE_MODE=skip — nothing to do.")
        return

    # --- docker mode ------------------------------------------------------
    if cfg.release_mode == "docker":
        from captain import docker

        docker.obtain_builder(cfg)
        sha = _resolve_git_sha(git_sha, cfg.project_dir)

        env_args: list[str] = [
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

        docker.run_captain_in_builder(cfg, ["release-publish"], extra_docker_args=env_args)
        docker.fix_docker_ownership(cfg, ["/work/out"])
        return

    # --- native mode ------------------------------------------------------
    missing = check_release_dependencies()
    if missing:
        log.error("Missing release tools: %s", ", ".join(missing))
        log.error("Install them or set --release-mode=docker.")
        raise SystemExit(1)

    sha = _resolve_git_sha(git_sha, cfg.project_dir)
    tag = oci.compute_version_tag(cfg.project_dir, sha, exclude=version_exclude)
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
