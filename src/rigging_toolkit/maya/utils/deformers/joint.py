from ..api import get_mobject

import maya.cmds as cmds
from maya.api import OpenMaya as om2

from typing import List

import logging

logger = logging.getLogger(__name__)

def clean_joint_rotation(joint):
    # type: (str) -> None
    """  Clean the joint rotations by getting absolute local matrix and setting rotations to jointOrient """
    dag_node = get_mobject(joint)
    if not dag_node.hasFn(om2.MFn.kJoint) or not dag_node.hasFn(om2.MFn.kTransform):
        return
    mfn_dag = om2.MFnDagNode(dag_node)
    object_world_mtx_plug = mfn_dag.findPlug("worldMatrix", False)
    object_world_mtx_plug.evaluateNumElements()
    world_mtx_elem = object_world_mtx_plug.elementByPhysicalIndex(0).asMObject()
    mfn_mtxData = om2.MFnMatrixData(world_mtx_elem)
    object_world_mtx = mfn_mtxData.matrix()

    object_parent_world_mtx_plug = mfn_dag.findPlug("parentMatrix", False)
    object_parent_world_mtx_plug.evaluateNumElements()
    parent_world_mtx_elem = object_parent_world_mtx_plug.elementByPhysicalIndex(0).asMObject()
    mfn_mtxData = om2.MFnMatrixData(parent_world_mtx_elem)
    object_parent_mtx = mfn_mtxData.matrix()

    object_local_mtx = object_world_mtx * object_parent_mtx.inverse()

    object_tmtx = om2.MTransformationMatrix(object_local_mtx)

    rotation = object_tmtx.rotation()

    # TODO replcace try catch with check if attributes are connected
    try:  # try in case there are connections
        mfn_dag.findPlug("jointOrientX", False).setDouble(rotation.x)
        mfn_dag.findPlug("jointOrientY", False).setDouble(rotation.y)
        mfn_dag.findPlug("jointOrientZ", False).setDouble(rotation.z)

        mfn_dag.findPlug("rotateX", False).setDouble(0.0)
        mfn_dag.findPlug("rotateY", False).setDouble(0.0)
        mfn_dag.findPlug("rotateZ", False).setDouble(0.0)
    except:
        logger.warning("Did not reset " + mfn_dag.name())
        
def clean_joint_rotation_for(joints):
    # type: (List[str]) -> None
    for joint in joints:
        clean_joint_rotation(joint)

def clean_joint_rotation_for_selected():
    # type: () -> None
    clean_joint_rotation_for(cmds.ls(sl=1,exactType="joint"))

