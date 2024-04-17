from maya import cmds
import numpy as np
import six
import operator
import logging
from typing import List, Optional, Union, Tuple
from rigging_toolkit.core.filesystem import Path
from rigging_toolkit.core.filesystem import find_new_version
from rigging_toolkit.maya.utils.api.dag import get_dag_path_api_2
import maya.api.OpenMaya as om2


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
    logger.info(f"Mesh {mesh} successfully exported to {str(path)}")

def export_versioned_mesh(mesh, folder):
    # type: (str, Path) -> None
    root = get_mesh_path(mesh)
    new_version, _ = find_new_version(folder, mesh, "abc")
    cmds.AbcExport(
        j=f"-frameRange 1 1 -uvWrite -dataFormat ogawa -root {root} -file {str(new_version)}"
    )
    logger.info(f"Mesh {mesh} successfully exported to {str(new_version)}")

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
    logger.info(f"{meshes} checking for shaders")
    for mesh in meshes:
        shaders = get_shaders_from_mesh(mesh)
        if shaders is None:
            logger.info(f"shaders not found on {mesh}")
            continue
        logger.info(shaders)
        for shader in shaders:
            if not shader in collected_shaders:
                collected_shaders.append(shader)

    return collected_shaders

def get_shading_group_from_shader(shader):
    # type: (str) -> str
    if not cmds.objExists(shader):
        logger.warning(f"shader: {shader} doesn't exist")
        return
    
    shader_set = cmds.listConnections(shader, d=True, et=True, t="shadingEngine")[0]
    return shader_set

def assign_shader(meshes, shader):
    # type: (List[str], str) -> None
    for mesh in meshes:
        if not cmds.objExists(mesh):
            logger.warning(f"Failed to assign {shader} to {mesh} -- {mesh} doesn't exist...")
            return
    if not cmds.objExists(shader):
        logger.warning(f"Failed to assign {shader} to {mesh} -- {shader} doesn't exist...")
        return
    # cmds.select(cl=True)
    # cmds.select(mesh)
    # logger.info(f"selected mesh: {mesh} being assigned to {shader}")
    # cmds.hyperShade(assign=shader)
    # cmds.select(cl=True)
    
    logger.warning(f"shader being used is: {shader}")

    shading_group = get_shading_group_from_shader(shader)

    if not shading_group:
        logger.warning(f"failed to assign shader to {meshes}, no shading group found")
        return
    
    cmds.sets(meshes, e=True, forceElement=shading_group)

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

def sphere_center(mesh):
    # type: (Union[str, List[str]]) -> Tuple[om2.MPoint, float]
    """Find the center sphere-like mesh.

    Args:
        mesh: name of the mesh to find the center from.

    Returns:
        (tuple): tuple containing:
            center (om2.MPoint)
            radius (float)
    """

    if isinstance(mesh, six.string_types):
        vertices = cmds.ls(f"{mesh}.vtx[*]", flatten=True)
    elif isinstance(mesh, list) and isinstance(mesh[0], six.string_types):
        vertices = cmds.ls(mesh, flatten=True)

    pts = [om2.MPoint(cmds.xform(v, q=True, t=True, ws=True)) for v in vertices]
    num_pts = len(pts)

    # build system.
    A = np.zeros((num_pts - 1, 3))
    b = np.zeros((num_pts - 1, 1))

    for i in range(num_pts - 1):
        A[i, 0] = 2 * (pts[i + 1].x - pts[0].x)
        A[i, 1] = 2 * (pts[i + 1].y - pts[0].y)
        A[i, 2] = 2 * (pts[i + 1].z - pts[0].z)

        b[i, 0] = (
            pts[i + 1].x ** 2
            + pts[i + 1].y ** 2
            + pts[i + 1].z ** 2
            - pts[0].x ** 2
            - pts[0].y ** 2
            - pts[0].z ** 2
        )

    # solve least square system
    # https://numpy.org/doc/stable/reference/generated/numpy.linalg.lstsq.html
    # convert results to python list.
    center = np.linalg.lstsq(A, b)[0].flatten().tolist()

    # estimate radius
    center_pt = om2.MPoint(center[0], center[1], center[2])
    r = 0.0
    for i in range(num_pts):
        r += pts[i].distanceTo(center_pt)

    r /= num_pts

    return center_pt, r

def closest_uv_from_point(mesh, point, space=om2.MSpace.kWorld):
    # type: (str, om2.MPoint, om2.MSpace) -> List[float]
    mesh_path = get_dag_path_api_2(mesh)

    mesh_path.extendToShape()
    mfn_mesh = om2.MFnMesh(mesh_path)

    u, v, _ = mfn_mesh.getUVAtPoint(point, space)
    return [u, v]

def closest_vertex_from_point(mesh, point, space=om2.MSpace.kWorld):
    # type: (str, om2.MPoint, om2.MSpace) -> int
    mesh_path = get_dag_path_api_2(mesh)
    mesh_path.extendToShape()
    mfn_mesh = om2.MFnMesh(mesh_path)

    face_index = mfn_mesh.getClosestPoint(point, space)[-1]
    face_vertices = mfn_mesh.getPolygonVertices(face_index)  # type: List[int]

    vertex_distances = (
        (vertex, mfn_mesh.getPoint(vertex, space).distanceTo(point))
        for vertex in face_vertices
    )
    closest_vertex = min(vertex_distances, key=operator.itemgetter(1))[0]

    return closest_vertex

def get_index_from_axis(axis):
    # type: (str) -> Optional[int]
    '''
    Returns an index based on the provided axis

    Args:
        axis -> string representing a valid axis, "x", "y" or "z"

    Return:
        axis_mapping -> An int representing the axis index, or None
    '''
    axis_mapping = {'x': 0, 'y': 1, 'z': 2}
    return axis_mapping.get(axis) or 0

def order_vertices_by_axis(vertices, axis="x"):
    # type: (List[str], Optional[str]) -> Tuple[List[str], List[str]]
    axis_idx = get_index_from_axis(axis)
    all_positive = [x for x in vertices if cmds.xform(x, query=True, worldSpace=True, translation=True)[axis_idx] >=0]
    all_negative = [x for x in vertices if cmds.xform(x, query=True, worldSpace=True, translation=True)[axis_idx] < 0]

    ascending_order = sorted(all_positive, key=lambda vert: cmds.xform(vert, query=True, worldSpace=True, translation=True)[axis_idx])
    descending_order = sorted(all_negative, key=lambda vert: cmds.xform(vert, query=True, worldSpace=True, translation=True)[axis_idx], reverse=True)

    return ascending_order, descending_order

def mirror_pos_by_axis(pos, mirror_axis="x"):
    # type: (List[float], Optional[str]) -> List[float]
    '''
    Mirrors world/object space by provided axis

    Args:
        pos -> List of three float values [0, 1, 2]
        mirror axis -> string representing a valid axis, "x", "y" or "z"
    
    Return:
        pos -> List of three float values with axis idx mirrored
    '''
    if len(pos) != 3:
        raise ValueError(f"Position {pos} is invalid")
    idx = get_index_from_axis(mirror_axis.lower())
    if idx is None:
        raise ValueError(f"Mirror axis {mirror_axis} is invalid")
    pos[idx] = -pos[idx]
    return pos

def mirror_vertex_by_pos(mesh, vtx, mirror_axis="x", space="world"):
    # type: (str, int, Optional[str], Optional[str]) -> int
    '''
    Mirrors vertex pos by provided axis and space 

    Args:
        mesh -> string representing mesh name
        vtx -> int representing vertex
        mirror axis -> string representing a valid axis, "x", "y" or "z"
        space -> string representing valid space position, "object" or "world"
                default's to world if string is invalid or not provided
    
    Return:
        closest_vertex -> int representing closest vertex to from mirrored pos
    '''
    if space.lower() == "object":
        vtx_pos = cmds.xform("{}.vtx[{}]".format(mesh, vtx), q=True, os=True, t=True)
    else:
        vtx_pos = cmds.xform("{}.vtx[{}]".format(mesh, vtx), q=True, ws=True, t=True)
    mirrored_world_space = mirror_pos_by_axis(vtx_pos, mirror_axis)
    mirrored_point = om2.MPoint(mirrored_world_space)
    closest_vertex = closest_vertex_from_point(mesh, mirrored_point)
    return closest_vertex

def mirror_vertices_by_edge(mesh, edge_id, v_ids):
    # type: (str, int, List[int]) -> List[int]
    
    # build symmetric data.
    cmds.select('{}.e[{}]'.format(mesh, edge_id))
    cmds.symmetricModelling(symmetry=True, topoSymmetry=True)
    
    # enter vertex selection mode
    cmds.selectType(vertex=True)   
    
    sym_ids = []
    for v in v_ids:
        cmds.select('{}.vtx[{}]'.format(mesh, v), replace=True, symmetry=True)
    
        verts = cmds.ls(sl=True, flatten=True)
        ids = [ int(vert.split('.vtx')[-1][1:-1]) for vert in verts if vert.find(".vtx") != -1]
        if len(ids) == 1:
            sym_ids.append(v)
        elif len(ids) == 2:
            sym_ids.append( sum(ids) - v )
        else:
            cmds.error("couldn't find symmetric for {}".format(v) )
    
    # reset
    cmds.symmetricModelling(symmetry=False, topoSymmetry=False)
    cmds.selectType(vertex=False)
    cmds.selectMode(object=True)
    cmds.select(clear=True)
    return sym_ids