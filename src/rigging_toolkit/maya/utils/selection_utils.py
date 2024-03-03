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

def delete_history(selection):
    # type: (List[str]) -> None
    for sel in selection:
        cmds.delete(sel, ch=True)

def parent_shapes(selection):
    shapes = []
    transforms_to_delete = []
    if not all(x for x in selection if cmds.objectType(x, isType="transform")):
        return
    for sel in selection[1:]:
        shp = cmds.listRelatives(sel, s=True)
        shapes.extend(shp)
        transforms_to_delete.append(sel)
    cmds.parent(shapes, selection[0], r=True, s=True)
    cmds.delete(transforms_to_delete)
    cmds.select(cl=1)

def set_shapes_reference_display(selection):
    for i in selection:
        shapes = cmds.listRelatives(i, s=True, c=True)
        for shp in shapes:
            cmds.setAttr(f"{shp}.overrideEnabled", 1)
            cmds.setAttr(f"{shp}.overrideDisplayType", 2)

def ls_transforms():
    # type: () -> List[str]
    return cmds.ls(sl=1, tr=1)

def ls_meshes():
    # type: () -> List[str]
    all_selected_transforms = ls_transforms()
    return [x for x in all_selected_transforms if cmds.listRelatives(x, s=True)]

def ls_shapes():
    # type: () -> List[str]
    shapes = []
    for x in ls():
        shps = cmds.listRelatives(x, s=True)
        shapes.extend(shps)

def ls_joints():
    # type: () -> List[str]
    return cmds.ls(sl=1, et="joint")

def ls_all():
    # type: () -> List[str]
    return cmds.ls()