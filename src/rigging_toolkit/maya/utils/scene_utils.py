from maya import cmds
import logging

logger = logging.getLogger(__name__)

def delete_namespaces():
    # type: () -> None
    # Set root namespace
    cmds.namespace(setNamespace=':')

    # Collect all namespaces except for the Maya built ins.
    all_namespaces = [x for x in cmds.namespaceInfo(listOnlyNamespaces=True, recurse=True) if x != "UI" and x != "shared"]

    if all_namespaces:
        # Sort by hierarchy, deepest first.
        all_namespaces.sort(key=len, reverse=True)
        for namespace in all_namespaces:
            # When a deep namespace is removed, it also removes the root. So check here to see if these still exist.
            if cmds.namespace(exists=namespace) is True:
                cmds.namespace(removeNamespace=namespace, mergeNamespaceWithRoot=True)

def delete_unknown_nodes():
    # type: () -> None
    unknown_nodes = cmds.ls(type="unknown")
    if unknown_nodes:
        cmds.delete(unknown_nodes)

    # Find and remove unknown plugins
    unknown_plugins = cmds.unknownPlugin(query=True, list=True)
    if unknown_plugins:
        for plugin in unknown_plugins:
            try:
                cmds.unknownPlugin(plugin, remove=True)
            except Exception as error:
                # Oddly enough, even if a plugin is unknown, it can still have a dependency in the scene.
                # So in this case, we log the error to look at after.
                logging.warning("Unknown plugin cannot be removed due to ERROR: {}".format(error))