import maya.api.OpenMaya as om2
import maya.cmds as cmds
import maya.OpenMaya as om1
import logging

logger = logging.getLogger(__name__)

def get_dag_path_api_1(node):
    # type: (str) -> om1.MDagPath

    path = om1.MDagPath()

    sel_list = om1.MSelectionList()

    try:
        sel_list.add(node)
        sel_list.getDagPath(0, path)
        return path
    except RuntimeError:
        raise RuntimeError("{0} doesn't exists in the scene".format(node))


def get_dag_path_api_2(node):
    # type: (str) -> om2.MDagPath

    if not cmds.objExists(node):
        logger.error("Object {0} does not exist!".format(node))
    selection_list = om2.MSelectionList()
    selection_list.add(node)
    return selection_list.getDagPath(0)