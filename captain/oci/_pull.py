"""Pull and tag operations for OCI artifacts."""

from __future__ import annotations

import logging
from pathlib import Path

from captain import skopeo

from ._common import _image_ref

log = logging.getLogger(__name__)


def pull(
    *,
    registry: str,
    repository: str,
    artifact_name: str,
    tag: str,
    target: str,
    output_dir: Path,
) -> None:
    """Pull and extract OCI artifacts.

    *target* may be ``"amd64"``, ``"arm64"``, or ``"combined"``.  The tag
    suffix is ``-{target}`` for single architectures, or bare ``{tag}``
    for ``"combined"``.
    """
    tag_suffix = "" if target == "combined" else f"-{target}"
    ref = _image_ref(registry, repository, artifact_name, f"{tag}{tag_suffix}")
    skopeo.export_image(ref, output_dir)

    # Recap
    extracted = sorted(f.name for f in Path(output_dir).iterdir() if f.is_file())
    log.info("")
    log.info("Pull complete")
    log.info("  Image:  %s", ref)
    log.info("  Target: %s", target)
    log.info("  Artifacts:")
    for name in extracted:
        log.info("    - %s", name)


def tag_image(
    *,
    registry: str,
    repository: str,
    artifact_name: str,
    src_tag: str,
    new_tag: str,
) -> None:
    """Tag an existing OCI artifact image with a new version."""
    src_ref = _image_ref(registry, repository, artifact_name, src_tag)
    dest_ref = _image_ref(registry, repository, artifact_name, new_tag)
    skopeo.copy(src_ref, dest_ref)
    log.info("Tagged %s → %s", src_ref, new_tag)


def tag_all(
    *,
    registry: str,
    repository: str,
    artifact_name: str,
    src_tag: str,
    new_tag: str,
    arches: list[str],
) -> None:
    """Tag all artifact images (per-arch + combined) with a new version."""
    all_tags = []
    for a in arches:
        arch_orig_tag = f"{src_tag}-{a}"
        arch_new_tag = f"{new_tag}-{a}"

        if len(arches) == 1:
            arch_new_tag = new_tag

        log.info("Tagging for arch %s → %s", arch_orig_tag, arch_new_tag)
        tag_image(
            registry=registry,
            repository=repository,
            artifact_name=artifact_name,
            src_tag=arch_orig_tag,
            new_tag=arch_new_tag,
        )
        all_tags.append((arch_orig_tag, arch_new_tag))

    # if both arm64 and amd64 arches, also tag the combined image.
    if set(arches) >= {"amd64", "arm64"}:
        # Tag the combined image (no arch suffix).
        log.info("Tagging combined image %s → %s", src_tag, new_tag)
        tag_image(
            registry=registry,
            repository=repository,
            artifact_name=artifact_name,
            src_tag=src_tag,
            new_tag=new_tag,
        )
        all_tags.append((src_tag, new_tag))

    # Recap
    image = f"{registry}/{repository}/{artifact_name}"
    log.info("")
    log.info("Tag complete")
    log.info("  Image:  %s", image)
    # log all_tags with arrows
    for src, dest in all_tags:
        log.info("  %s  →  %s", src, dest)
