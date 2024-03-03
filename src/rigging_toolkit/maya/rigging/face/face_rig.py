from rigging_toolkit.maya.rigging.eyes import build_eye_rig
from rigging_toolkit.maya.utils.deformers.skincluster import import_skin_weights
from rigging_toolkit.maya.utils.deformers.general import deformers_by_type
from rigging_toolkit.maya.shapes.shape_graph import ShapeGraph
from rigging_toolkit.maya.assets.asset_manager import import_asset, import_character_assets
from rigging_toolkit.maya.utils.rigging_utils import create_follicle_jnts_at_vertices
from rigging_toolkit.maya.utils.mesh_utils import order_vertices_by_axis

from rigging_toolkit.core import Context, find_latest
from maya import cmds
import json
import time
import logging

logger = logging.getLogger(__name__)

class FaceRig(object):

    def __init__(self, context):
        # type: (Context) -> None
        self.context = context
        self._assets = []
        self.build()

    def build(self):
        st = time.time()
        cmds.file(new=True, f=True)
        self.import_body_rig()
        self.import_assets()
        ShapeGraph(self.context, load_neutral=False)
        self.import_teeth_eyes_module()
        self.import_UI()
        self.setup_UI()
        self.setup_eyebrows()
        self.import_weights()
        elapsed_time = time.time() - st
        logger.info(f'Execution time: {time.strftime("%H:%M:%S", time.gmtime(elapsed_time))}')

    def import_UI(self):
        #type: () -> None

        face_ui_path = self.context.rigs_path / "ui"

        latest, _ =  find_latest(face_ui_path, f"{self.context.character_name}_face_ui", "ma")

        cmds.file(str(latest), i=True, uns=False)

        cmds.parent("Face_UI", "controls")

        parent_constraint = cmds.parentConstraint("root_ctrl", "head_ctrl", "Face_UI", mo=True, w=0)[0]
        reverse_node = cmds.createNode("reverse", n="Eyes_C_Follow_Reverse")
        cmds.connectAttr("offFaceControls_CON.Follow_Head", f"{reverse_node}.inputX")
        cmds.connectAttr("offFaceControls_CON.Follow_Head", f"{parent_constraint}.head_ctrlW1")
        cmds.connectAttr(f"{reverse_node}.outputX", f"{parent_constraint}.root_ctrlW0")

    def import_teeth_eyes_module(self):
        # type: () -> None

        modules_path = self.context.rigs_path / "modules"
        
        latest, _ = find_latest(modules_path, "teeth_eyes_rig", "ma")

        cmds.file(str(latest), i=True, uns=False)

        jnts = ["jaw", "r_eye_jnt", "l_eye_jnt"]

        cmds.parent(jnts, "head")
        cmds.parent("Jaw_Rig_GRP", "head_ctrl")
        cmds.parent("Eye_Rig_GRP", "controls")

        parent_constraint = cmds.parentConstraint("root_ctrl", "head_ctrl", "Eye_C_CON", mo=True, w=0, sr=["x", "y", "z"])[0]
        reverse_node = cmds.createNode("reverse", n="Eye_C_CON_Follow_Reverse")
        cmds.connectAttr("Eye_C_CON.Follow_Head", f"{reverse_node}.inputX")
        cmds.connectAttr("Eye_C_CON.Follow_Head", f"{parent_constraint}.head_ctrlW1")
        cmds.connectAttr(f"{reverse_node}.outputX", f"{parent_constraint}.root_ctrlW0")

    def import_body_rig(self):
        # type: () -> None

        modules_path = self.context.rigs_path / "modules"
        
        latest, _ = find_latest(modules_path, "body_rig", "ma")

        cmds.file(str(latest), i=True, uns=False)

    def import_assets(self):
        # type: () -> None

        assets = import_character_assets(self.context, ignore_list=["eyelashes"], return_nodes=True)
        assets = [x.replace("|", "") for x in assets if "Shape" not in x]
        self._assets.extend(assets)
        cmds.parent(assets, "export_geometry")

    def import_weights(self):
        # type: () -> None
        for asset in self._assets:
            weights_path = self.context.rigs_path / "weights"
            weights, _ = find_latest(weights_path, asset, "xml")
            if weights is None:
                continue
            import_skin_weights(asset, weights)

    def setup_UI(self):
        # type: () -> None

        data_path = self.context.rigs_path / "data"

        ui_setup_json, _ = find_latest(data_path, "ui_setup", "json")

        blendshape = deformers_by_type("geo_head_L1", "blendShape")[0]
        
        with open(ui_setup_json, "r") as f:
            data = json.load(f)

        for connection in data["shape_connections"]:
            for shp, values in connection.items():
                cmds.setDrivenKeyframe(blendshape, at=shp, v=0, dv=values["neutral_value"], cd=f"{values['control']}.{values['axis']}", itt="linear", ott="linear")
                cmds.setDrivenKeyframe(blendshape, at=shp, v=1, dv=values["driver_value"], cd=f"{values['control']}.{values['axis']}", itt="linear", ott="linear")

        for connection in data["joint_connections"]:
            for jnt, values in connection.items():
                cmds.setDrivenKeyframe(jnt, at=values["jnt_axis"], v=values["neutral_jnt_value"], dv=values["neutral_value"], cd=f"{values['control']}.{values['axis']}", itt="linear", ott="linear")
                cmds.setDrivenKeyframe(jnt, at=values["jnt_axis"], v=values["driver_jnt_value"], dv=values["driver_value"], cd=f"{values['control']}.{values['axis']}", itt="linear", ott="linear")
        

    def setup_eyebrows(self):
        # type: () -> None
        data_path = self.context.rigs_path / "data"

        eyebrow_json, _ = find_latest(data_path, "eyebrow_data", "json")

        with open(eyebrow_json, "r") as f:
            data = json.load(f)

        main_key = list(data.keys())[0]

        lower_keys_dict = data[main_key]

        mesh = lower_keys_dict["mesh"]
        vertices = lower_keys_dict["vertices"]

        left_vertices, right_vertices = order_vertices_by_axis(vertices)

        left_jnts, left_follicles = create_follicle_jnts_at_vertices(mesh, left_vertices, name="left_eyebrow")

        right_jnts, right_follicles = create_follicle_jnts_at_vertices(mesh, right_vertices, name="right_eyebrow")

        eyebrow_node = cmds.createNode("transform", n="eyebrow_rig")
        eyebrow_follicle_node = cmds.createNode("transform", n="eyebrow_follicles", p=eyebrow_node)
        eyebrow_jnt_node = cmds.createNode("transform", n="eyebrow_jnts", p=eyebrow_node)

        cmds.parent(left_jnts, right_jnts, eyebrow_jnt_node)
        cmds.parent(left_follicles, right_follicles, eyebrow_follicle_node)

        cmds.parent(eyebrow_node, "DO_NOT_TOUCH")
        cmds.setAttr(f"{eyebrow_node}.visibility", 0)

