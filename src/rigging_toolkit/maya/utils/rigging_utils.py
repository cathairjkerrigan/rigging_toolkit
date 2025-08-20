from maya import cmds
from typing import Optional, Union, List, Tuple
from rigging_toolkit.maya.utils.mesh_utils import sphere_center, closest_uv_from_point
import maya.api.OpenMaya as om2

AXIS = ["x", "y", "z"]

def set_controller_color(shape, color):
    # type: (str, int) -> None
    cmds.setAttr(f"{shape}.overrideEnabled", 1)
    cmds.setAttr(f"{shape}.overrideColor", color)

def set_scale(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.s{i}", value)

def set_rotation(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.r{i}", value)

def set_translation(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.t{i}", value)

def lock_translate(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.t{i}", l=lock)

def lock_rotation(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.r{i}", l=lock)

def lock_scale(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.s{i}", l=lock)

def toggle_visibility(object):
    # type: (str) -> None
    visibility_state = cmds.getAttr(f"{object}.v")
    if visibility_state == 0:
        cmds.setAttr(f"{object}.v", 1)
    else:
        cmds.setAttr(f"{object}.v", 0)

def toggle_template(object):
    # type: (str) -> None
    template_state = cmds.getAttr(f"{object}.template")
    if template_state == 0:
        cmds.setAttr(f"{object}.template", 1)
    else:
        cmds.setAttr(f"{object}.template", 0)

def joint_label(transform, name, side):

    cmds.setAttr(f"{transform}.side", side)
    cmds.setAttr(f"{transform}.type", 18)
    cmds.setAttr(f"{transform}.otherType", name, typ='string')

def center_eye_joint(joint, mesh):
    # type: (str, Union[str, List[str]]) -> None
    """Places the given joint in the center of the mesh

    Note:
        the joint can really be any transform node.
        the mesh does't need to be an eye either, but is mostly used for this.
    """
    center, _ = sphere_center(mesh)
    cmds.xform(joint, worldSpace=True, translation=(center.x, center.y, center.z))

def create_follicle_jnts_at_vertices(mesh, vertices, name="follicle_jnt"):
    # type: (str, List[str], Optional[str]) -> Tuple[List[str], List[str]]
    joints = []
    follicles = []
    count = 1    
    for vtx in vertices:
        ws_pos = cmds.xform(vtx, ws=True, q=True, t=True)
        m_point = om2.MPoint(ws_pos)
        uv = closest_uv_from_point(mesh, m_point)
        jnt = cmds.createNode("joint", n=f"{name}_{count:02d}_jnt")
        cmds.xform(jnt, ws=True, t=ws_pos)
        follicle = cmds.createNode("follicle", n=f"{name}_{count:02d}_follicleShape")
        transform = cmds.listRelatives(follicle, parent=True, fullPath=True)[0]  # type: str
        follicle = cmds.listRelatives(transform, shapes=True, fullPath=True)[0]
        transform = cmds.rename(transform, f"{name}_{count:02d}_follicle")

        cmds.connectAttr(f"{mesh}.outMesh", f"{follicle}.inputMesh")
        cmds.connectAttr(
            f"{mesh}.worldMatrix[0]", f"{follicle}.inputWorldMatrix"
        )
        cmds.connectAttr(
            f"{follicle}.outTranslate", f"{transform}.translate"
        )
        cmds.connectAttr(f"{follicle}.outRotate", f"{transform}.rotate")

        cmds.setAttr(f"{follicle}.parameterU", uv[0])
        cmds.setAttr(f"{follicle}.parameterV", uv[1])
        
        follicle_t_pos = cmds.xform(transform, query=True, translation=True, worldSpace=True)
        follicle_r_pos = cmds.xform(transform, query=True, rotation=True, worldSpace=True)
        cmds.xform(jnt, ws=True, t=follicle_t_pos)
        cmds.xform(jnt, ws=True, rotation=follicle_r_pos)
        cmds.parentConstraint(transform, jnt, mo=0)
        joints.append(jnt)
        follicles.append(transform)
        count += 1

    return joints, follicles