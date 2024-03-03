from rigging_toolkit.maya.rigging.eyes import build_eye_rig
from rigging_toolkit.maya.shapes.shape_graph import ShapeGraph
from rigging_toolkit.maya.assets import import_character_assets
from rigging_toolkit.core import Context, find_latest

class BuildRig(object):
    
    def __init__(self, context):
        # type: (Context) -> None
        self.context = context

        self.build()

    def build(self):
        self.import_rig()
        ShapeGraph(self.context)
        build_eye_rig(self.context)

    def import_UI(self):
        #type: () -> None

        face_ui_path = self.context.rigs_path / "ui"

        latest, _ =  find_latest(face_ui_path, f"{self.context.character_name}_face_ui", "ma")

