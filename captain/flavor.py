"""Flavor-specific configuration."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Protocol, runtime_checkable

import jinja2

from captain.config import Config

log = logging.getLogger(__name__)


@runtime_checkable
class BaseFlavor(Protocol):
    cfg: Config
    id: str
    name: str
    description: str
    flavor_dir: Path
    supported_architectures: frozenset[str]
    template_map: dict[str, list[Path]]
    static_map: dict[str, Path]

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        if cfg is None:
            raise ValueError("cfg (Config) cannot be None")
        self.cfg = cfg

        if flavor_dir is None:
            raise ValueError("flavor_dir (Path) cannot be None")
        if not flavor_dir.is_dir():
            raise ValueError(f"flavor_dir {flavor_dir} does not exist or is not a directory")
        self.flavor_dir = flavor_dir

        self.template_map = {}
        self.static_map = {}
        log.debug("Called BaseFlavor.setup()...")
        pass

    def generate(self):
        log.debug("Called BaseFlavor.generate()...")
        # Before generating, cleanup known targets. @TODO make dir disposable instead
        log.debug("Cleaning up old generated files in %s", self.cfg.project_dir)
        shutil.rmtree(self.cfg.project_dir / "mkosi.conf", ignore_errors=True)
        shutil.rmtree(self.cfg.project_dir / "mkosi.postinst", ignore_errors=True)
        shutil.rmtree(self.cfg.project_dir / "mkosi.finalize", ignore_errors=True)
        shutil.rmtree(self.cfg.project_dir / "mkosi.extra", ignore_errors=True)

        self.copy_static_files(self.cfg.project_dir)
        self.render_templates(self.cfg.project_dir)  # For compatibility
        pass

    def specific_flavor_dir(self, flavor_id: str) -> Path:
        flavor_id_underscore = flavor_id.replace("-", "_")
        flavor_dir = self.cfg.project_dir / "captain" / "flavors" / flavor_id_underscore

        if not flavor_dir.is_dir():
            log.error(
                "Specific Flavor dir '%s' not found. Expected to find directory %s",
                flavor_id,
                flavor_dir,
            )
            raise SystemExit(1)
        return flavor_dir

    def render_templates(self, output_dir: Path):
        log.debug("Called BaseFlavor.render_templates() with output_dir: %s", output_dir)
        # Use jinja2 to render all templates in self.template_map, writing output to output_dir
        # The keys of self.template_map are the relative output paths (e.g. "mkosi.conf"), and the
        # values are lists of Path objects pointing to Jinja2 template files.
        # If more than one template is provided for a given output path, they should be rendered
        # in order and concatenated together to produce the final output file.
        for relative_output_path, template_paths in self.template_map.items():
            log.debug(
                "Rendering templates for output path '%s': %s",
                relative_output_path,
                template_paths,
            )
            rendered_content = ""
            for template_path in template_paths:
                log.debug("Rendering template %s", template_path)
                # Here you would load the template file, render it with the appropriate context
                # (e.g. using Jinja2), and append the rendered content to rendered_content.
                # For example:
                template = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(template_path.parent)
                ).get_template(template_path.name)
                rendered_content += template.render(cfg=self.cfg)

            output_file_path = output_dir / relative_output_path
            log.debug("Writing rendered content to %s", output_file_path)
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(rendered_content)

            # Make output_file executable @TODO: we will need a way to tell
            output_file_path.chmod(output_file_path.stat().st_mode | 0o111)

    def copy_static_files(self, project_dir):
        # Do a plain copy of all files in self.static_map to project_dir / relative_path, where
        # relative_path is the key in self.static_map
        for relative_path, source_path in self.static_map.items():
            destination_path = project_dir / relative_path
            log.debug("Copying static file from '%s' to '%s'", source_path, destination_path)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination_path)


def create_and_setup_flavor_for_id(flavor_id: str, cfg: Config) -> BaseFlavor:
    flavor_id_underscore = flavor_id.replace("-", "_")
    flavor_dir = cfg.project_dir / "captain" / "flavors" / flavor_id_underscore

    if not flavor_dir.is_dir():
        log.error(
            "Flavor '%s' not found. Expected to find directory %s",
            flavor_id,
            flavor_dir,
        )
        raise SystemExit(1)

    wanted_module = f"captain.flavors.{flavor_id_underscore}"
    log.debug("Attempting to import flavor module %s from directory %s", wanted_module, flavor_dir)

    try:
        module = __import__(wanted_module, fromlist=["create_flavor"])
    except ImportError as e:
        log.error(
            "Failed to import flavor module %s from directory %s: %s",
            wanted_module,
            flavor_dir,
            e,
        )
        raise e

    # Validate API explicitly
    if not hasattr(module, "create_flavor"):
        log.error("Flavor module %s does not define create_flavor()", wanted_module)
        raise SystemExit(1)

    log.debug("Executing %s.create_flavor()", wanted_module)
    flavor: BaseFlavor = module.create_flavor()

    if not isinstance(flavor, BaseFlavor):
        log.error(
            "create_flavor() in %s did not return BaseFlavor (got %r)",
            wanted_module,
            type(flavor),
        )
        raise SystemExit(1)

    log.debug("Calling setup() on flavor %s with config: %s", flavor, cfg)
    flavor.setup(cfg, flavor_dir)

    log.debug(
        "Flavor is setup; description: %s; supported_architectures: %s",
        flavor.description,
        flavor.supported_architectures,
    )

    return flavor
