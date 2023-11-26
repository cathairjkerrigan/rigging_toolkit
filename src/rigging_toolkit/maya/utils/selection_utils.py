from maya import cmds
from typing import List, Optional, Tuple, Any
from maya.api import OpenMaya

def reset_attributes_to_default(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            current_value = cmds.getAttr("{}.{}".format(obj, attr))
            default_value = cmds.attributeQuery(attr, node=obj, listDefault=True)[0]

            if current_value != default_value:
                cmds.setAttr("{}.{}".format(obj, attr), default_value)

def unlock_unhide_keyable_attrs(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            cmds.setAttr("{}.{}".format(obj, attr), lock=False, keyable=True)

def lock_keyable_attrs(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            cmds.setAttr("{}.{}".format(obj, attr), lock=True)

def delete_keyframes_from_selection(selection):
    # type: (List) -> None
    cmds.cutKey(selection, s=True)

def select_hiearchy(selection):
    # type: (List) -> None
    cmds.select(selection, hi=True)

def ls():
    # type: () -> List
    return cmds.ls(sl=1)

def selection_with_components():
    # type: () -> Tuple[List[Any], List[Any]]
    selected = cmds.ls(selection=True, long=True)
    edges_faces = cmds.filterExpand([x for x in selected if '.' in x], selectionMask=[32, 34], fullPath=True) or []
    vtx = cmds.polyListComponentConversion(edges_faces, toVertex=True) or []
    components = cmds.filterExpand(selected + vtx, selectionMask=[28, 31]) or []
    nodes = [x for x in selected if '.' not in x]

    return nodes, components

def build_handle(position, name = "Handle_0"):
    # type: (OpenMaya.MVector, Optional[str]) -> str
    transform_node = cmds.createNode("transform", name=name)
    cmds.setAttr(f"{transform_node}.displayHandle", True)
    cmds.setAttr(f"{transform_node}.translate", *position)
    return transform_node

    
def baricentre_from_selection(place_handle=False):
    # type: (Optional[bool]) -> OpenMaya.MVector
    nodes, components = selection_with_components()
    count = len(components) + len(nodes)
    pos = OpenMaya.MVector()
    for node in nodes:
        pos += OpenMaya.MVector(cmds.xform(node, query=True, translation=True, worldSpace=True))
    for component in components:
        pos += OpenMaya.MVector(cmds.pointPosition(component))
    pos /= count

    if place_handle:
        build_handle(pos)

def get_shaders_from_selection():
    # type: () -> List[str]
    
    shapes_in_sel = cmds.ls(dag=1,o=1,s=1,sl=1)
    
    shading_groups = cmds.listConnections(shapes_in_sel, type='shadingEngine')
    
    shaders = cmds.ls(cmds.listConnections(shading_groups),materials=1)
    
    return shaders
