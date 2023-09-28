from maya import cmds
from typing import List

TEMPLATE_OFF = 0
TEMPLATE_ON = 1


def get_all_shapes():
    # type: () -> List
    return cmds.ls(exactType="mesh")

def query_template_display(node):
    # type: (str) -> int
    current_display = cmds.getAttr("{}.overrideEnabled".format(node))
    if current_display == TEMPLATE_ON:
        display = TEMPLATE_OFF
    else:
        display = TEMPLATE_ON
    return display

def toggle_template_display(node):
    # type: (List) -> None
    display = query_template_display(node)
    cmds.setAttr("{}.overrideEnabled".format(node), display)
    cmds.setAttr("{}.overrideDisplayType".format(node), display)
    
def toggle_template_display_for_all_meshes():
    # type: () -> None
    all_meshes = get_all_shapes()
    for mesh in all_meshes:
        toggle_template_display(mesh)