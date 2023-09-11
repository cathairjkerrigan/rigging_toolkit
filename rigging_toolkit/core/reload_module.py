import sys

from logging import getLogger
import importlib
import sys

logger = getLogger(__name__)

def reload_module(module_name):
    try:
        if sys.version_info[0] == 2:
            # Python 2.x
            module = __import__(module_name)
            reload(module)
        else:
            # Python 3.x
            import importlib
            module = importlib.import_module(module_name)
            importlib.reload(module)
        logger.info("Module {} reloaded successfully.".format(module_name))
        
        if hasattr(module, '__all__'):
            submodule_names = module.__all__
        else:
            submodule_names = [name for name in dir(module) if isinstance(getattr(module, name), type(module))]
        
        # Recursively reload submodules
        for submodule_name in submodule_names:
            submodule = sys.modules.get('{}.{}'.format(module_name, submodule_name))
            if submodule:
                if sys.version_info[0] == 2:
                    reload(submodule)
                else:
                    importlib.reload(submodule)
                logger.info("Submodule {} reloaded successfully.".format(submodule.__name__))
    except Exception as e:
        logger.error("Error reloading module {}: {}".format(module_name, e))
