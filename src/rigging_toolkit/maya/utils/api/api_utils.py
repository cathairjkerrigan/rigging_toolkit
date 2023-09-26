import maya.api.OpenMaya as om2

def get_mobject(node):
    # type: (str) -> om2.MObject
    sel = om2.MSelectionList().add(node)
    return sel.getDependNode(0)
