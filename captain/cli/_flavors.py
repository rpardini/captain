"""``captain list-flavors`` — the flavor registry, for humans and for CI.

``--github-output`` emits ``name=value`` lines for ``$GITHUB_OUTPUT``: the build matrices
(with and without the CaptainOS kernel build) and the multi-arch "combined" publish matrix.
``--release`` emits one ``<flavor-id> <target> <arch> <tag-suffix>`` line per flavor, for the
release workflow (``while read -r id target arch suffix``); the tag suffix may be empty.
"""

from __future__ import annotations

import json
import logging

import click
from rich.table import Table

import captain
from captain.cli._main import cli
from captain.flavor import Flavor
from captain.flavors import FLAVORS
from captain.traits.platform import AcpiCaptainKernel
from captain.util import get_arch_info

log = logging.getLogger(__name__)


def _is_combined(flavor: Flavor) -> bool:
    """Published as one multi-arch image, built from both arches' artifacts (see ci.yml)."""
    return flavor.supported_architectures == {"amd64", "arm64"}


def _matrix_entries(flavor: Flavor) -> list[dict[str, str | bool]]:
    return [
        {
            "arch": arch,
            "output_arch": get_arch_info(arch).output_arch,
            "captainos_kernel": isinstance(flavor.platform, AcpiCaptainKernel),
            "iso": flavor.has_iso(),
            "cache": flavor.ci_cache,
            "FLAVOR_ID": flavor.id,
        }
        for arch in sorted(flavor.supported_architectures)
    ]


@cli.command("list-flavors", short_help="List flavors (table, JSON, or GitHub Actions matrices).")
@click.option("--json", "as_json", is_flag=True, help="Print one JSON object per flavor.")
@click.option("--github-output", is_flag=True, help="Print name=value matrices for $GITHUB_OUTPUT.")
@click.option("--release", is_flag=True, help="Print '<id> <target> <arch> <tag-suffix>' lines.")
def list_flavors_cmd(as_json: bool, github_output: bool, release: bool) -> None:
    """List the flavors in the registry (captain/flavors.py)."""
    if github_output:
        entries = [e for f in FLAVORS for e in _matrix_entries(f)]
        with_kernel = [e for e in entries if e["captainos_kernel"]]
        without_kernel = [e for e in entries if not e["captainos_kernel"]]
        combined = [
            {"combined_flavor": f.id, "iso": f.has_iso()} for f in FLAVORS if _is_combined(f)
        ]
        click.echo(f"matrix_with_kernel={json.dumps({'include': with_kernel})}")
        click.echo(f"matrix={json.dumps({'include': without_kernel})}")
        click.echo(f"matrix_combined={json.dumps({'include': combined})}")
        return

    if release:
        for f in FLAVORS:
            target = "combined" if _is_combined(f) else sorted(f.supported_architectures)[0]
            arch = "amd64" if target == "combined" else target
            click.echo(f"{f.id} {target} {arch} {f.tag_suffix}".rstrip())
        return

    if as_json:
        for f in FLAVORS:
            entry = {
                "id": f.id,
                "description": f.description,
                "arches": sorted(f.supported_architectures),
                "distro": f.distro.name,
                "platform": f.platform.name,
                "role": f.role.name,
                "output": f.output.name,
                "iso": f.has_iso(),
                "combined": _is_combined(f),
                "ci_cache": f.ci_cache,
                "tag_suffix": f.tag_suffix,
            }
            click.echo(json.dumps(entry))
        return

    table = Table(title="Flavors", show_header=True, header_style="bold magenta")
    for column in ("id", "arches", "distro", "platform", "role", "output", "iso"):
        table.add_column(column)
    for f in FLAVORS:
        table.add_row(
            f.id,
            ",".join(sorted(f.supported_architectures)),
            f.distro.name,
            f.platform.name,
            f.role.name,
            f.output.name,
            "yes" if f.has_iso() else "no",
        )
    captain.console.print(table)
