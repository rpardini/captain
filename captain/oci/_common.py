"""Shared constants and helpers for the OCI package."""

from __future__ import annotations

import logging

_ARCHES = ("amd64", "arm64")

log = logging.getLogger(__name__)


def _image_ref(registry: str, repository: str, artifact_name: str, tag: str) -> str:
    """Build a fully-qualified OCI image reference."""
    return f"{registry}/{repository}/{artifact_name}:{tag}"
