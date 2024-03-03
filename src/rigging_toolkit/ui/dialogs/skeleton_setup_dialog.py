from typing import Optional

import json
import logging

from PySide2 import QtWidgets, QtCore
from maya import cmds
from rigging_toolkit.core.filesystem import find_latest, find_new_version
from rigging_toolkit.maya.utils.deformers.skincluster import import_skin_weights
from rigging_toolkit.maya.utils import ls_meshes, scene_cleanup
from rigging_toolkit.core.context import Context
from rigging_toolkit.maya.assets.asset_manager import import_asset
from rigging_toolkit.ui.widgets.process_textedit import ProcessTextEdit

logger = logging.getLogger(__name__)

class SetupSkeletonDialog(QtWidgets.QDialog):

    def __init__(self, context=None, parent=None):
        # type: (Optional[Context], Optional[QtWidgets.QDialog]) -> None

        super(SetupSkeletonDialog, self).__init__(parent=parent)

        self.setWindowTitle("Setup Skeleton Tool")

        self.context = context

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        # process info
        self._process_info_groupbox = QtWidgets.QGroupBox("Process Info")

        self._process_info_layout = QtWidgets.QVBoxLayout()

        self._process_info_groupbox.setLayout(self._process_info_layout)

        self._process_info = ProcessTextEdit()

        self._process_info_layout.addWidget(self._process_info)

        self._layout.addWidget(self._process_info_groupbox)

        # utils
        self._utils_groupbox = QtWidgets.QGroupBox("Utils")

        self._utils_layout = QtWidgets.QVBoxLayout()

        self._utils_groupbox.setLayout(self._utils_layout)

        self._layout.addWidget(self._utils_groupbox)

        # joints
        self._joints_layout = QtWidgets.QGridLayout()

        self._jaw_label = QtWidgets.QLabel("Jaw Joint: ")
        self._jaw_lineedit = QtWidgets.QLineEdit()
        self._jaw_lineedit.setText("jaw")

        self._tongue_label = QtWidgets.QLabel("Tongue Joint: ")
        self._tongue_lineedit = QtWidgets.QLineEdit()
        self._tongue_lineedit.setText("tongue01")

        self._joints_layout.addWidget(self._jaw_label, 0, 0)
        self._joints_layout.addWidget(self._jaw_lineedit, 0, 1)
        self._joints_layout.addWidget(self._tongue_label, 1, 0)
        self._joints_layout.addWidget(self._tongue_lineedit, 1, 1)
        self._utils_layout.addLayout(self._joints_layout)

        # setup 
        self._setup_layout = QtWidgets.QGridLayout()

        self._setup_pushbutton = QtWidgets.QPushButton("Setup")
        self._realign_pushbutton = QtWidgets.QPushButton("Realign")
        self._apply_weights_checkbox = QtWidgets.QCheckBox("Apply Weights")
        self._select_pushbutton = QtWidgets.QPushButton("Select")
        self._clean_pushbutton = QtWidgets.QPushButton("Cleanup")

        self._setup_layout.addWidget(self._setup_pushbutton, 0, 0)
        self._setup_layout.addWidget(self._realign_pushbutton, 0, 1)
        self._setup_layout.addWidget(self._clean_pushbutton, 0, 2)
        self._setup_layout.addWidget(self._apply_weights_checkbox, 1, 0)
        self._setup_layout.addWidget(self._select_pushbutton, 1, 1)
        self._utils_layout.addLayout(self._setup_layout)

        # setup connections
        self._setup_pushbutton.clicked.connect(self._on_setup_clicked)
        self._realign_pushbutton.clicked.connect(self._on_realign_clicked)
        self._select_pushbutton.clicked.connect(self._on_select_clicked)
        self._clean_pushbutton.clicked.connect(self._on_cleanup_clicked)


    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context

    def _on_setup_clicked(self):
        # type: () -> None
        if not self._apply_weights_checkbox.isChecked():
            self._process_info.add_warning("Skipping Weights ...")
        else:
            self._process_info.add_success("Importing Weights ...")
            self._import_weights()
        self._setup_locators()
        self._create_jaw_sdk()

        min_frame = cmds.playbackOptions(ast=True, q=True)
        max_frame = cmds.playbackOptions(aet=True, q=True)
        cmds.playbackOptions(edit=True, minTime=0, maxTime=10)

    def _on_realign_clicked(self):
        # type: () -> None
        """Align jaw and tongue to new positions"""
        # type: () -> None
        self._process_info.add_success("Realigning Jaw and Tongue ...")

        # reset timeline to 0
        cmds.currentTime(0)
        tongue_name = self._tongue_lineedit.text()
        tongue_loc_name = "{}_loc".format(tongue_name)

        cmds.select(clear=True)

        rotation_loc = cmds.xform(tongue_loc_name, q=True, ro=1, ws=1)
        translation_loc = cmds.xform(tongue_loc_name, q=True, t=1, ws=1)
        cmds.xform(tongue_name, t=translation_loc, ro=rotation_loc, ws=1)
        cmds.select(clear=True)

        logger.info(
            "The {} was matched to {} {}".format(
                tongue_name, rotation_loc, translation_loc
            )
        )

    def _on_select_clicked(self):
        # type: () -> None
        """Select the jaw joint and locator to realign"""
        # type: () -> None
        jaw_jnt_name = self._jaw_lineedit.text()
        jaw_loc_name = "{}_dyn_restpose_loc".format(jaw_jnt_name)

        cmds.select([jaw_jnt_name, jaw_loc_name])

    def _import_weights(self):
        # type: () -> None
        weights_path = self.context.rigs_path / "weights"
        for mesh in ls_meshes():
            latest, _ = find_latest(weights_path, mesh, "xml")
            if not latest:
                continue
            import_skin_weights(mesh, latest)

    def _setup_locators(self):
        """Setup the locators"""
        # type: () -> None

        jaw_jnt_name = self._jaw_lineedit.text()
        jaw_loc_name = "{}_dyn_restpose_loc".format(jaw_jnt_name)

        if not cmds.objExists(jaw_loc_name):
            jaw_loc = cmds.spaceLocator(name=jaw_loc_name)[0]

            constraint = cmds.parentConstraint(jaw_jnt_name, jaw_loc, mo=0)
            cmds.delete(constraint)

        tongue_jnt_name = self._tongue_lineedit.text()
        tongue_loc_name = "{}_loc".format(tongue_jnt_name)

        if not cmds.objExists(tongue_loc_name):
            tongue_loc = cmds.spaceLocator(name=tongue_loc_name)[0]

            constraint = cmds.parentConstraint(tongue_jnt_name, tongue_loc, mo=0)
            cmds.delete(constraint)

        matrix_dic = self._get_skin_cluster_connections()

        for sk, value in matrix_dic.items():
            if "matrix" in sk:
                cmds.connectAttr(
                    str(jaw_loc) + ".worldInverseMatrix[0]",
                    str(sk.replace(".matrix", ".bindPreMatrix")),
                    f=1,
                )
                logger.info(
                    "Successfully connected {} to {} ".format(
                        str(jaw_loc) + ".worldInverseMatrix[0]",
                        str(sk.replace(".matrix", ".bindPreMatrix")),
                    )
                )

    def _get_skin_cluster_connections(self):
        """Get matrix connections from skincluster"""
        # type: () -> None
        jaw_skin_cluster_list, jaw_matrix_list = self._get_skin_cluster_connections_for(
            self._jaw_lineedit.text()
        )
        (
            tongue_skin_cluster_list,
            tongue_matrix_list,
        ) = self._get_skin_cluster_connections_for(self._tongue_lineedit.text())

        skin_cluster_list = jaw_skin_cluster_list + tongue_skin_cluster_list
        matrix_list = jaw_matrix_list + tongue_matrix_list

        matrix_dic = {}
        for sk_cluster, matrix in zip(skin_cluster_list, matrix_list):
            matrix_dic.update({sk_cluster: matrix})

        logger.info(":dictonary was {} was successfully created".format(matrix_dic))
        return matrix_dic

    def _get_skin_cluster_connections_for(self, name):
        skin_cluster_list = cmds.listConnections(name, d=1, p=1, t="skinCluster")
        if not skin_cluster_list:
            logger.error("Could not find skinClusters on {}".format(name))
            return [], []
        skincluster_set = set(cmds.listConnections(name, d=1, p=1, t="skinCluster"))
        histList = list(skincluster_set)

        skin_cluster_list = []
        for sk in histList:
            if "matrix" in sk:
                skin_cluster = sk
                skin_cluster_list.append(skin_cluster)

        matrix_list = []
        for i in skin_cluster_list:
            matrix_connections = cmds.listConnections("{}".format(i), d=True, p=1)
            matrix_list.append(matrix_connections[0])
        return skin_cluster_list, matrix_list

    def _create_jaw_sdk(self):
        """Align jaw and tongue to new positions"""
        # type: () -> None
        jaw_joint_name = self._jaw_lineedit.text()
        keyframe_info = [[0, [0, 0, 0]], [10, [0, 0, -18]]]
        for ki in keyframe_info:
            cmds.currentTime(ki[0])
            logger.info("current time set to {}".format(0))
            for at, v in zip(["rx", "ry", "rz"], ki[1]):
                cmds.setKeyframe(
                    "{}".format(jaw_joint_name), v=v, at=at, itt="linear", ott="linear"
                )
                logger.info("key {} set on {}".format(str(ki[1]), jaw_joint_name))

    def _on_cleanup_clicked(self):
        """Clean the scene after completing the realignment"""
        # type: () -> bool
        tongue_jnt_name = self._tongue_lineedit.text()
        tongue_loc_name = "{}_loc".format(tongue_jnt_name)
        jaw_jnt_name = self._jaw_lineedit.text()
        jaw_loc_name = "{}_dyn_restpose_loc".format(jaw_jnt_name)
        # reset timeline to 0
        cmds.currentTime(0, edit=True)
        # delete all in scene
        if cmds.objExists(tongue_loc_name) and cmds.objExists(jaw_loc_name):
            cmds.delete([tongue_loc_name, jaw_loc_name])
        reference_nodes = cmds.ls(rf=True)
        for reference in reference_nodes:
            reference_query = cmds.referenceQuery(reference, filename=True)
            cmds.file(reference_query, rr=True)
        forster_parent_nodes = cmds.ls(type="fosterParent")
        cmds.delete(forster_parent_nodes)
        anim_curve = cmds.ls(type="animCurveTA")
        cmds.delete(anim_curve)
        scene_cleanup()
        return True

