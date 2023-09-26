import sys

from logging import getLogger
import importlib

logger = getLogger(__name__)

def reload_module(module_name, include_submodules=False):
    # type: (str, bool) -> None

    message = "Reloading {}".format(module_name)
    if include_submodules:
        message += " and its submodules"
    message += "."

    logger.info(message)

    unload_modules = []  # type: List[str]

    for module in sys.modules.copy():
        should_delete = False
        if include_submodules:
            if module_name in module:
                should_delete = True
        else:
            if module == module_name:
                should_delete = True

        if should_delete:
            unload_modules.append(module)

    for module in unload_modules:
        print(module)
        del sys.modules[module]
        print("deleted module: {}".format(module))
