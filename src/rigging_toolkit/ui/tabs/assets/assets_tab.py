from typing import Optional
from rigging_toolkit.core.context import Context
from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets
from rigging_toolkit.maya.shaders import export_selected_shaders, setup_shaders
from rigging_toolkit.maya.assets import export_all_character_assets, import_character_assets, export_selected_character_assets
from rigging_toolkit.core.filesystem import has_folders, find_latest
from maya import cmds

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

