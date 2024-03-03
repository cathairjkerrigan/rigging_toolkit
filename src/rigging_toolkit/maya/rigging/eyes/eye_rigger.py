import logging
import os
import json

from rigging_toolkit.maya.rigging.eyes.aer_no_ui import AER
import pymel.core as pm
from rigging_toolkit.core.filesystem import find_latest
from rigging_toolkit.maya.utils.deformers.skincluster import import_skin_weights
from rigging_toolkit.maya.utils.mesh_utils import sphere_center
from rigging_toolkit.core import Context
from maya import cmds

logger = logging.getLogger(__name__)


def build_eye_rig(context):
    # type: (Context) -> None 
    
    eyes_folder = context.assets_path / "eyes" / "meshes"
    eyes_name = "geo_eyes_L1"
    eyes_file, _ = find_latest(eyes_folder, eyes_name, "abc")
    cmds.file(str(eyes_file), i=True)

    rigging_data_path = context.rigs_path / "data"

    # use this to find eyeball names, vertices, sides etc
    eyes_data_path, _ = find_latest(rigging_data_path, "eye_rig", "json")

    with open(str(eyes_data_path), "r") as f:
        eyes_data = json.load(f)

    for side, data in eyes_data.items():
        name = data["name"]
        mesh = cmds.ls(data["eye_mesh"], flatten=True)
        upper_lid_vertices = data["upper_lid_vertices"]
        lower_lid_vertices = data["lower_lid_vertices"]
        parent_jnt = data["parent_jnt"] if data["parent_jnt"] else None
        parent_ctrl = data["parent_ctrl"] if data["parent_ctrl"] else None
        parent_grp = data["parent_grp"] if data["parent_grp"] else None

        pivot, _ = sphere_center(mesh)

        locator = cmds.spaceLocator(
            n=f"{side}_eye_pivot_locator",
        )[0]
        cmds.xform(locator, ws=1, t=[pivot.x, pivot.y, pivot.z])
        AER(
            rig_name=name,
            eye_locator=locator,
            upper_lid_vertices=upper_lid_vertices,
            lower_lid_vertices=lower_lid_vertices,
            parent_jnt=parent_jnt,
            parent_control=parent_ctrl,
            parent_grp=parent_grp
        )