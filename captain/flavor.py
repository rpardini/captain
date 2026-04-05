"""Flavor-specific configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

from captain.config import Config

log = logging.getLogger(__name__)


@runtime_checkable
class BaseFlavor(Protocol):
    cfg: Config
    id: str
    name: str
    description: str
    supported_architectures: set[str]

    def setup(self, cfg: Config, flavor_dir: Path) -> None:
        # assert cfg is not None, "setup() must be called with a Config before accessing self.cfg"
        if cfg is None:
            raise ValueError("cfg (Config) cannot be None")
        self.cfg = cfg
        log.debug("Called BaseFlavor.setup(), which does nothing.")
        pass

    def generate(self):
        log.debug("Called BaseFlavor.generate(), which does nothing.")
        pass


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
