"""Helpers for the Armbian-next apt repository.

Armbian flavors pull stable meta-package names (``linux-image-edge-rockchip64``
etc.) whose underlying kernel version changes whenever armbian-next republishes.
The repo's ``Release`` file ETag is a cheap proxy for "the repo changed": folding
it into the flavor hash makes CI rebuild (and ship the newer kernel) instead of
reusing a stale cached build.
"""

from __future__ import annotations

import hashlib
import logging
import urllib.error
import urllib.request

log = logging.getLogger(__name__)

# The `armbian` dist (where the linux-image kernel packages live). A single
# repo-wide token from this Release file applies to all armbian flavors.
ARMBIAN_NEXT_RELEASE_URL = "https://apt-test.next.armbian.com/dists/armbian/Release"

_FETCH_TIMEOUT = 30  # seconds


def release_etag(url: str = ARMBIAN_NEXT_RELEASE_URL) -> str:
    """Return a short, stable cache-bust token from *url*'s ETag response header.

    Returns ``""`` on any failure or when the server sends no ETag — an empty
    token means "no cache-bust", preserving current behaviour.
    """
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            etag = resp.headers.get("ETag", "")
    except (urllib.error.URLError, OSError) as exc:
        log.warning("Could not fetch ETag from %s (%s); no armbian cache-bust", url, exc)
        return ""

    # Normalise weak-validator prefix and surrounding quotes, then hash to a
    # fixed-width token that is safe to embed in filenames / cache keys.
    etag = etag.strip().removeprefix("W/").strip('"')
    if not etag:
        log.warning("No ETag header from %s; no armbian cache-bust", url)
        return ""

    token = hashlib.sha256(etag.encode()).hexdigest()[:16]
    log.info("Armbian repo Release ETag %r → cache-bust token %s", etag, token)
    return token
