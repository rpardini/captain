"""Click-based CLI for CaptainOS.

Provides the ``captain`` console script with subcommands:

- ``builder``  — build the Docker builder image, optionally push it
- ``build``    — full build pipeline (tools → initramfs → iso → artifacts)
- ``release-publish`` — publish artifacts as OCI images via buildah

Shell completion is available for bash and zsh::

    # bash
    eval "$(_CAPTAIN_COMPLETE=bash_source captain)"

    # zsh
    eval "$(_CAPTAIN_COMPLETE=zsh_source captain)"
"""

from captain.click._main import main

__all__ = ["main"]
