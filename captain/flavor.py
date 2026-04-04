"""Flavor-specific configuration."""

from __future__ import annotations

import logging
import sys
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
    # create_flavor() is defined in files in /flavors/<flavor_id>/<flavor_id>.py
    # and returns a BaseFlavor
    flavor_dir = cfg.project_dir / "flavors" / cfg.flavor_id
    flavor_python_file_path = flavor_dir / f"{cfg.flavor_id}.py"
    if not flavor_python_file_path.is_file():
        log.error(
            "Flavor '%s' not found. Expected to find %s", cfg.flavor_id, flavor_python_file_path
        )
        raise SystemExit(1)

    # We import the flavor module dynamically, using importlib
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        f"flavors.{cfg.flavor_id}", flavor_python_file_path
    )
    if spec is None or spec.loader is None:
        log.error("Failed to load flavor module from %s", flavor_python_file_path)
        raise SystemExit(1)

    log.debug("Loaded flavor module spec from %s: %s", flavor_python_file_path, spec)

    flavor_module = importlib.util.module_from_spec(spec)

    log.debug("Registering flavor module %s in sys.modules under name %s", flavor_module, spec.name)
    sys.modules[spec.name] = flavor_module


    spec.loader.exec_module(flavor_module)

    log.debug("Executing flavor module %s's create_flavor() function", flavor_module)
    flavor: BaseFlavor = flavor_module.create_flavor()


    log.debug("Calling setup() on flavor %s with config: %s", flavor, cfg)
    flavor.setup(cfg, flavor_dir)

    return flavor
