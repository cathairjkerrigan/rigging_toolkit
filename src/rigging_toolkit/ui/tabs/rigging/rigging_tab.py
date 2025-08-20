from typing import Optional
from rigging_toolkit.core import Context, find_new_version, find_latest, Path
from rigging_toolkit.ui.widgets import TabWidget
from rigging_toolkit.ui.dialogs import SetupSkeletonDialog
from rigging_toolkit.maya.utils import ls_meshes, ls_joints
from rigging_toolkit.maya.utils.rigging_utils import center_eye_joint
from rigging_toolkit.maya.utils.deformers.skincluster import import_skin_weights, export_skin_weights, transfer_skin_cluster
from PySide2 import QtWidgets
import logging

logger = logging.getLogger(__name__)

class RiggingTab(TabWidget):
    TAB_NAME = "Rigging Tab"

    def __init__(self, parent=None, context=None):
        super(TabWidget, self).__init__(parent=parent)
        self.context = context
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        # skin weights groupbox
        self._skin_weights_layout = QtWidgets.QVBoxLayout()

        self._skin_weights_groupbox = QtWidgets.QGroupBox("Weights")

        self._skin_weights_groupbox.setLayout(self._skin_weights_layout)

        # search and replace layout/widgets
        self._name_overwrite_layout = QtWidgets.QHBoxLayout()
        self._name_overwrite_label = QtWidgets.QLabel("Name Override: ")
        self._name_overwrite_search_lineedit = QtWidgets.QLineEdit()
        self._name_overwrite_search_lineedit.setPlaceholderText("Search")
        self._name_overwrite_replace_lineedit = QtWidgets.QLineEdit()
        self._name_overwrite_replace_lineedit.setPlaceholderText("Replace")
        self._name_overwrite_layout.addWidget(self._name_overwrite_label)
        self._name_overwrite_layout.addWidget(self._name_overwrite_search_lineedit)
        self._name_overwrite_layout.addWidget(self._name_overwrite_replace_lineedit)
        self._skin_weights_layout.addLayout(self._name_overwrite_layout)

        # skin weight utils layout/widgets
        self._skin_weights_utils_layout = QtWidgets.QGridLayout()
        self._import_skin_weights_pushbutton = QtWidgets.QPushButton("Import Skin Weights")
        self._export_skin_weights_pushbotton = QtWidgets.QPushButton("Export Skin Weights")
        self._transfer_skin_weights_pushbutton = QtWidgets.QPushButton("Transfer Skin Cluster")
        self._skin_weights_utils_layout.addWidget(self._import_skin_weights_pushbutton, 0, 0)
        self._skin_weights_utils_layout.addWidget(self._export_skin_weights_pushbotton, 0, 1)
        self._skin_weights_utils_layout.addWidget(self._transfer_skin_weights_pushbutton, 1, 0, 1, 2)
        self._skin_weights_layout.addLayout(self._skin_weights_utils_layout)
        self._import_skin_weights_pushbutton.clicked.connect(self._on_import_skin_weights_clicked)
        self._export_skin_weights_pushbotton.clicked.connect(self._on_export_skin_weights_clicked)
        self._transfer_skin_weights_pushbutton.clicked.connect(self._on_transfer_skin_weights_clicked)

        # utils groupbox
        self._utils_layout = QtWidgets.QVBoxLayout()

        self._utils_groupbox = QtWidgets.QGroupBox("Utils")

        self._utils_groupbox.setLayout(self._utils_layout)

        self._button_layout = QtWidgets.QGridLayout()

        self._utils_layout.addLayout(self._button_layout)

        self._skeleton_setup_pushbutton = QtWidgets.QPushButton("Jaw Alignment Tool")
        self._center_eye_joint_pushbutton = QtWidgets.QPushButton("Center Eye Joint")
        self._button_layout.addWidget(self._skeleton_setup_pushbutton, 0, 0)
        self._button_layout.addWidget(self._center_eye_joint_pushbutton, 0, 1)
        self._skeleton_setup_pushbutton.clicked.connect(self._on_skeleton_setup_clicked)
        self._center_eye_joint_pushbutton.clicked.connect(self._on_center_eye_clicked)

        self._layout.addWidget(self._skin_weights_groupbox)
        self._layout.addWidget(self._utils_groupbox)

    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context
        self.child_dialogs = [c for c in self.child_dialogs if c != None]
        for c in self.child_dialogs:
            c._on_context_changed(context)
        
    def _on_import_skin_weights_clicked(self):
        # type: () -> None
        weights_path = self.context.rigs_path / "weights"
        for mesh in ls_meshes():
            file_name = self._search_and_replace(mesh)
            latest, _ = find_latest(weights_path, file_name, "xml")
            if latest is None:
                logger.error(f"Could not find weights for {file_name} in {weights_path}")
                return
            import_skin_weights(mesh, latest)

    def _on_export_skin_weights_clicked(self):
        # type: () -> None
        weights_path = Path.validate_path(self.context.rigs_path / "weights", create_missing=True)
        for mesh in ls_meshes():
            file_name = self._search_and_replace(mesh)
            new_file, _ = find_new_version(weights_path, file_name, "xml")
            export_skin_weights(mesh, new_file)

    def _on_transfer_skin_weights_clicked(self):
        # type: () -> None
        selection = ls_meshes()
        if not selection:
            return
        source_mesh = selection[0]
        target_mesh = selection[1]
        transfer_skin_cluster(source_mesh, target_mesh)

    def _search_and_replace(self, name):
        # type: (str) -> str
        return name.replace(self._search_string(), self._replace_string())
    
    def _search_string(self):
        # type: () -> str
        return self._name_overwrite_search_lineedit.text()
    
    def _replace_string(self):
        # type: () -> str
        return self._name_overwrite_replace_lineedit.text()
    
    def _on_skeleton_setup_clicked(self):
        dialog = SetupSkeletonDialog(self.context, self)
        self.child_dialogs.append(dialog)
        dialog.show()

    def _on_center_eye_clicked(self):
        mesh = ls_meshes()[0]
        joint = ls_joints()[0]
        center_eye_joint(joint, mesh)
