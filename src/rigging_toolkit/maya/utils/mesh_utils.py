from maya import cmds
import logging
from typing import List, Optional
from pathlib import Path
from rigging_toolkit.core.filesystem import find_new_version

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

def export_versioned_mesh(mesh, folder):
    # type: (str, Path) -> None
    root = get_mesh_path(mesh)
    new_version, _ = find_new_version(folder, mesh, "abc")
    cmds.AbcExport(
        j=f"-frameRange 1 1 -uvWrite -dataFormat ogawa -root {root} -file {str(new_version)}"
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

def convert_to_vertex_list(inComponents):
    # type: (str) -> str
    convertedVertices = cmds.polyListComponentConversion(inComponents, tv=True)
    return cmds.filterExpand(convertedVertices, sm=31, fp=1)
    
def shortest_edge_path(start, end):
    # type: (str, str) -> str
    curMesh = start.split('.')[0]
    vertexNumber1 = int(start[start.index("[") + 1: -1])
    vertexNumber2 = int(end[end.index("[") + 1: -1])
    edgeSelection = cmds.polySelect(curMesh, shortestEdgePath=[vertexNumber1, vertexNumber2])
    if edgeSelection is None:
        cmds.error("selected vertices are not part of the same polyShell!")

    newVertexSelection = []
    for edge in edgeSelection:
        midexpand = convert_to_vertex_list(f"{curMesh}.e[{edge}]")
        newVertexSelection.append(midexpand)
    
    return newVertexSelection
    
def get_shaders_from_mesh(mesh):
    # type: (str) -> List[str]

    if not cmds.objExists(mesh):
        return
    
    shapes_in_mesh = cmds.ls(mesh, dag=1,o=1,s=1)
    
    shading_groups = cmds.listConnections(shapes_in_mesh, type='shadingEngine')
    
    shaders = cmds.ls(cmds.listConnections(shading_groups),materials=1)
    
    return shaders

def get_shaders_from_meshes(meshes):
    # type: (List[str]) -> List[str]
    collected_shaders = []

    for mesh in meshes:
        shaders = get_shaders_from_mesh(mesh)
        if shaders is None:
            continue
        for shader in shaders:
            if not shader in collected_shaders:
                collected_shaders.append(shader)

    return collected_shaders

def assign_shader(mesh, shader):
    # type: (str, str) -> None
    if not cmds.objExists(mesh):
        logger.warning(f"Failed to assign {shader} to {mesh} -- {mesh} doesn't exist...")
        return
    if not cmds.objExists(shader):
        logger.warning(f"Failed to assign {shader} to {mesh} -- {mesh} doesn't exist...")
        return
    cmds.select(mesh)
    cmds.hyperShade(assign=shader)
    cmds.select(cl=True)

def get_all_meshes():
    # type: () -> List[str]
    all_dag_objs = cmds.ls(dag=True, et="mesh")
    meshes = []
    for obj in all_dag_objs:
        parent = get_parent(obj)
        if not parent or parent in meshes:
            continue
        meshes.append(parent)

    return meshes

def has_uvset(mesh, uvset_name=None):
    # type: (str, str) -> bool
    uvsets = cmds.polyUVSet(mesh, query=True, allUVSets=True)
    has_uvset = uvset_name in uvsets if uvset_name else len(uvsets) > 0
    return has_uvset

def set_current_uvset(mesh, uvset):
    # type: (str, str) -> None
    cmds.polyUVSet(mesh, currentUVSet=True, uvSet=uvset)
        