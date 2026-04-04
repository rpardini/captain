"""Flavor-specific configuration."""

from __future__ import annotations

import logging
from pathlib import Path

from captain.config import Config

log = logging.getLogger(__name__)


class BaseFlavor:
    cfg: Config

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        # assert cfg is not None, "setup() must be called with a Config before accessing self.cfg"
        if cfg is None:
            raise ValueError("cfg (Config) cannot be None")
        self.cfg = cfg
        log.debug(
            f"Called generic version of {self.__class__.__name__}.setup(), which does nothing."
        )
        pass

    def generate(self):
        log.debug(
            f"Called generic version of {self.__class__.__name__}.generate(), which does nothing."
        )
        pass


def create_and_setup_flavor_for_id(flavor_id: str, cfg: Config) -> BaseFlavor:
    import importlib.util
    import sys

    flavor_dir = cfg.project_dir / "flavors" / flavor_id
    flavor_python_file_path = flavor_dir / f"{flavor_id}.py"

    if not flavor_python_file_path.is_file():
        log.error(
            "Flavor '%s' not found. Expected to find %s",
            flavor_id,
            flavor_python_file_path,
        )
        raise SystemExit(1)

    # Use a fully qualified, hierarchical module name
    module_name = f"captain.flavors.{flavor_id}.{flavor_id}"

    spec = importlib.util.spec_from_file_location(module_name, flavor_python_file_path)
    if spec is None or spec.loader is None:
        log.error("Failed to load flavor module from %s", flavor_python_file_path)
        raise SystemExit(1)

    log.debug("Loaded flavor module spec from %s: %s", flavor_python_file_path, spec)

    module = importlib.util.module_from_spec(spec)

    # Critical: set package for proper import + logging hierarchy
    module.__package__ = f"flavors.{flavor_id}"

    # Register before execution (required for imports + identity)
    sys.modules[module_name] = module

    spec.loader.exec_module(module)

    # Validate API explicitly
    if not hasattr(module, "create_flavor"):
        log.error("Flavor module %s does not define create_flavor()", module_name)
        raise SystemExit(1)

    log.debug("Executing %s.create_flavor()", module_name)
    flavor: BaseFlavor = module.create_flavor()

    if not isinstance(flavor, BaseFlavor):
        log.error(
            "create_flavor() in %s did not return BaseFlavor (got %r)",
            module_name,
            type(flavor),
        )
        raise SystemExit(1)

    log.debug("Calling setup() on flavor %s with config: %s", flavor, cfg)
    flavor.setup(cfg, flavor_dir)

    return flavor
