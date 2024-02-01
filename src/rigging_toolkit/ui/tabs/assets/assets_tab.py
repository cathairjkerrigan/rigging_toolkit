from typing import Optional
from rigging_toolkit.core.context import Context
from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets
from rigging_toolkit.maya.shaders import export_selected_shaders, setup_shaders
from rigging_toolkit.maya.assets import export_all_character_assets, import_character_assets, export_selected_character_assets
from rigging_toolkit.maya.shapes import export_shapes
from rigging_toolkit.ui.dialogs import WeightMapTool
from rigging_toolkit.ui.widgets import MultiMessageBox
from rigging_toolkit.maya.utils import deformers_by_type, list_shapes, ls, reset_blendshape_targets, export_blendshape_targets
import pprint
import logging

logger = logging.getLogger(__name__)

class AssetsTab(TabWidget):
    TAB_NAME = "Assets Tab"

    def __init__(self, parent=None, context=None):
        super(TabWidget, self).__init__(parent=parent)
        self.context = context
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self._assets_layout = QtWidgets.QVBoxLayout()

        self._assets_groupbox = QtWidgets.QGroupBox("Assets")

        self._assets_groupbox.setLayout(self._assets_layout)

        self._layout.addWidget(self._assets_groupbox)

        self._export_assets_layout = QtWidgets.QHBoxLayout()

        self._assets_layout.addLayout(self._export_assets_layout)

        self.export_all_assets_btn = QtWidgets.QPushButton("Export All Assets")
        self.export_all_assets_btn.clicked.connect(self._on_export_all_assets_clicked)

        self.export_selected_assets_btn = QtWidgets.QPushButton("Export Selected Assets")
        self.export_selected_assets_btn.clicked.connect(self._on_export_selected_assets_clicked)

        self.import_character_assets = QtWidgets.QPushButton("Import Character Assets")
        self.import_character_assets.clicked.connect(self._on_import_assets_clicked)

        self._export_assets_layout.addWidget(self.export_selected_assets_btn)
        self._export_assets_layout.addWidget(self.export_all_assets_btn)
        self._assets_layout.addWidget(self.import_character_assets)

        self._shaders_groupbox = QtWidgets.QGroupBox("Shaders")

        self._shaders_layout = QtWidgets.QHBoxLayout()

        self._shaders_groupbox.setLayout(self._shaders_layout)

        self._export_shaders_btn = QtWidgets.QPushButton("Export Shaders")
        self._export_shaders_btn.clicked.connect(self._on_export_shaders_clicked)
        self._import_shaders_btn = QtWidgets.QPushButton("Import Shaders")
        self._import_shaders_btn.clicked.connect(self._on_import_shaders_clicked)

        self._shapes_layout = QtWidgets.QVBoxLayout()

        self._shapes_groupbox = QtWidgets.QGroupBox("Shapes")

        self._shapes_groupbox.setLayout(self._shapes_layout)

        self._layout.addWidget(self._shapes_groupbox)

        self._shape_utils_layout = QtWidgets.QGridLayout()
        
        self._list_shapes_button = QtWidgets.QPushButton("List Shapes")
        self._list_shapes_button.clicked.connect(self._on_list_shapes_clicked)

        self._reset_shapes_button = QtWidgets.QPushButton("Reset Shapes")
        self._reset_shapes_button.clicked.connect(self._on_reset_shapes_clicked)

        self._export_shapes_button = QtWidgets.QPushButton("Export Shapes")
        self._export_shapes_button.clicked.connect(self._on_export_shapes_clicked)

        self._export_split_shapes_button = QtWidgets.QPushButton("Export Split Shapes")
        self._export_split_shapes_button.clicked.connect(self._on_export_split_shapes_clicked)

        self._shape_utils_layout.addWidget(self._list_shapes_button, 0, 0)
        self._shape_utils_layout.addWidget(self._reset_shapes_button, 0, 1)
        self._shape_utils_layout.addWidget(self._export_shapes_button, 1, 0)
        self._shape_utils_layout.addWidget(self._export_split_shapes_button, 1, 1)

        self._weight_map_layout = QtWidgets.QHBoxLayout()
    
        self._load_weight_map_tool = QtWidgets.QPushButton("Weight Map Tool")

        self._load_weight_map_tool.clicked.connect(self._on_load_weight_map_tool_clicked)

        self._weight_map_layout.addWidget(self._load_weight_map_tool)

        self._shapes_layout.addLayout(self._shape_utils_layout)
        self._shapes_layout.addLayout(self._weight_map_layout)

        self._shaders_layout.addWidget(self._export_shaders_btn)
        self._shaders_layout.addWidget(self._import_shaders_btn)

        self._layout.addWidget(self._shaders_groupbox)

    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context
        self.child_dialogs = [c for c in self.child_dialogs if c != None]
        for c in self.child_dialogs:
            c._on_context_changed(context)

    def _on_export_selected_assets_clicked(self):
        export_selected_character_assets(self.context)

    def _on_export_all_assets_clicked(self):
        export_all_character_assets(self.context)

    def _on_import_assets_clicked(self):
        import_character_assets(self.context)

    def _on_export_shaders_clicked(self):
        export_selected_shaders(self.context)

    def _on_import_shaders_clicked(self):
        setup_shaders(self.context)

    def _on_load_weight_map_tool_clicked(self):
        # type: () -> None
        dialog = WeightMapTool(context=self.context, parent=self)
        self.child_dialogs.append(dialog)
        dialog.show()

    def _on_list_shapes_clicked(self):
        # type: () -> None
        shapes = []
        selected_mesh = ls()
        blendshapes = deformers_by_type(selected_mesh[0], "blendShape")
        if not blendshapes:
            return
        for blendshape in blendshapes:
            current_shapes = list_shapes(blendshape)
            shapes.extend(current_shapes)

        if shapes:
            pprint.pprint(shapes)

    def _on_reset_shapes_clicked(self):
        # type: () -> None
        selected_mesh = ls()
        blendshapes = deformers_by_type(selected_mesh[0], "blendShape")
        if not blendshapes:
            return
        for blendshape in blendshapes:
            reset_blendshape_targets(blendshape)

    def _on_export_shapes_clicked(self):
        # type: () -> None

        message_box = MultiMessageBox()

        selected_mesh = ls()

        message_box.setup(
            "Export Shapes",
            f"Export Shapes to {str(self.context.shapes_path)}?",
            [("Yes", True), ("No", False)],
        )

        export_shapes_to_folder = message_box.exec_()

        if export_shapes_to_folder is None:
            logger.warning("Terminating Export Shapes...")
            return
        
        if export_shapes_to_folder is False:
            export_blendshape_targets(selected_mesh[0])
            return
        
        message_box.setup(
            "Export Shapes",
            f"Export Split Type?",
            [("Full Shapes", "full_shapes"), ("Split Shapes", "split_shapes"), ("No", False)]
        )

        export_type = message_box.exec_()

        if export_type is None:
            logger.warning("Terminating Export Shapes...")
            return
        
        if export_type is False:
            export_shapes(self.context)
            return
        
        export_shapes(self.context, split_type=export_type)

    def _on_export_split_shapes_clicked(self):
        # type: () -> None
        logger.warning("Export Split Shapes is currently not supported, need to add logic")
        pass
