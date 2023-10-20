from maya import cmds
import logging
from typing import List, Optional
from pathlib import Path

TEMPLATE_OFF = 0
TEMPLATE_ON = 1


logger = logging.getLogger(__name__)

def list_verticies(mesh):
    # type: (str) -> List
    return cmds.ls("{}.vtx[*]".format(mesh), fl=True)

def get_parent(mesh):
    # type: (str) -> Optional[str]
    parent = cmds.listRelatives(mesh, p=True)
    if parent:
        return parent[0]
    return None

def get_shapes(mesh):
    # type: (str) -> Optional[List]
    shapes = cmds.listRelatives(mesh, shapes=True)
    if shapes: 
        return shapes
    return None

def get_mesh_path(mesh):
    # type: (str) -> str
    return cmds.ls(mesh, long=True)[0]

def export_mesh(mesh, path):
    # type: (str, Path) -> None
    root = get_mesh_path(mesh)
    cmds.AbcExport(
        j=f"-frameRange 1 1 -uvWrite -dataFormat ogawa -root {root} -file {str(path)}"
    )

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
