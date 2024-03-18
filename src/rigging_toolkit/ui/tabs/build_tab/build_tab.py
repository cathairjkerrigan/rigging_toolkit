from typing import Optional
from rigging_toolkit.core.context import Context
from rigging_toolkit.ui.widgets import TabWidget, FileTableWidget
from PySide2 import QtWidgets
from rigging_toolkit.maya.rigging.face import FaceRig
from maya import cmds
from rigging_toolkit.core.filesystem import Path, find_versioned_files

class BuildTab(TabWidget):
    TAB_NAME = "Build Tab"

    def __init__(self, parent=None, context=None):
        super(TabWidget, self).__init__(parent=parent)
        self.context = context
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self._configuration_label = QtWidgets.QLabel("Build Type: ")
        self._configuration_combobox = QtWidgets.QComboBox()
        self._configuration_combobox.addItems(["Preview", "Save"])
        self._configuration_layout = QtWidgets.QHBoxLayout()
        self._configuration_layout.addWidget(self._configuration_label)
        self._configuration_layout.addWidget(self._configuration_combobox)

        self.build_button = QtWidgets.QPushButton("Build Rig")

        self._previous_builds_groupbox = QtWidgets.QGroupBox("Previous Builds")
        self._group_box_layout = QtWidgets.QVBoxLayout()
        self._previous_builds_groupbox.setLayout(self._group_box_layout)
        self._table_widget = FileTableWidget()
        self._group_box_layout.addWidget(self._table_widget)
        
        self._layout.addLayout(self._configuration_layout)
        self._layout.addWidget(self.build_button)
        self._layout.addWidget(self._previous_builds_groupbox)

        self.build_button.clicked.connect(self.build)

        self.populate_table()

    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context
        self.populate_table()
        self.child_dialogs = [c for c in self.child_dialogs if c != None]
        for c in self.child_dialogs:
            c._on_context_changed(context)

    def build(self):
        # type: () -> None
        build_type = self.get_build_type()
        FaceRig(self.context, build_type)
        if build_type:
            self.populate_table()

    def get_build_type(self):
        # type: () -> bool
        if self._configuration_combobox.currentIndex() <= 0:
            return False
        return True
    
    def populate_table(self):
        # type: () -> None
        self._table_widget.clearContents()
        build_path = self.context.builds_path
        files = find_versioned_files(build_path)
        for file in files:
            self._table_widget.add_file_entry(file.name, file.file_size, file.creation_date)
