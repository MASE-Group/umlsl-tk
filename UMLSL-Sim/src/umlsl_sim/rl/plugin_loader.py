"""Deferred population of the `type -> class` registries.

`algorithms`, `observations` and `rewards` are each a registry filled by a
decorator that runs when the module carrying it is imported, so every module in
the package has to be imported before a lookup can succeed. Doing that from the
package's ``__init__`` is the obvious way, but it makes *any* import of the
package -- including one that only wants its type enum -- drag in torch and
gymnasium. The control GUI does exactly that at startup, to name the dropdown
options, and paid seconds for an ML stack a plain NPC run never touches.

So the imports are deferred to the first registry lookup instead: `get_rl_algo`,
`get_observation_model` and `get_reward_model` call the package's
``load_plugins()`` before reading their dict, and nothing reaches a registry
except through them. Adding an algorithm or a reward is still a new module plus
a decorator, with no consumer to edit.
"""
from __future__ import annotations

import importlib
import pathlib
import pkgutil
from typing import Callable


def package_loader(package: str, init_file: str) -> Callable[[], None]:
    """Build the once-only ``load_plugins()`` for a registry package.

    Args:
        package: The package's ``__name__``.
        init_file: The package's ``__file__``.

    Returns:
        A function that imports every non-package module in it, first call only.
    """
    package_path = pathlib.Path(init_file).parent
    loaded = False

    def load_plugins() -> None:
        nonlocal loaded
        if loaded:
            return
        # Set before importing, not after: a plugin module that performs a
        # lookup while it is being imported would otherwise re-enter here.
        loaded = True
        for _, module_name, ispkg in pkgutil.iter_modules([str(package_path)]):
            if not ispkg:
                importlib.import_module(f"{package}.{module_name}")

    return load_plugins
