from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets, QtCore
from rigging_toolkit.maya.utils import list_shapes
import logging
from pathlib import Path
from rigging_toolkit.maya.utils.deformers.blendshape import (
    apply_weightmap_to_target,
    combine_weight_maps,
    get_weights_from_blendshape,
    get_weights_from_blendshape_target,
    inverse_target_weightmap,
    list_shapes,
    mirror_weight_map_by_pos,
    set_delta_weightmap_to_target,
    subtract_weight_maps,
    mirror_weight_map_by_topology_selection
)
from rigging_toolkit.maya.utils.weightmap import WeightMap

logger = logging.getLogger(__name__)

class WeightMapUtilsTab(TabWidget):
    TAB_NAME = "Weight Map Utils"
    REFRESH_SIGNAL = QtCore.Signal()

    def __init__(self, parent=None, file_path=None, blendshape=None):
        super(TabWidget, self).__init__(parent=parent)
        self.blendshape = blendshape
        self.file_path = file_path
        self.child_dialogs = []

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self._shape_listwidget = QtWidgets.QListWidget()
        self._shape_listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._layout.addWidget(self._shape_listwidget)

        self._button_layout = QtWidgets.QGridLayout()

        self._set_delta_weightmap_pushbutton = QtWidgets.QPushButton("Set Delta Weight Map")
        self._set_delta_weightmap_pushbutton.setToolTip(
            "Set target weight map to Delta weight map\n\n"
            "All vertices affected by the target will be flooded to a value of 1.0\n\n"
            "All other verticies not affected by the target will be flooded to a value of 0.0"
        )

        self._normalize_selected_pushbutton = QtWidgets.QPushButton("Normalize Selected")
        self._normalize_selected_pushbutton.setToolTip(
            "Normalize selected Weight Maps"
        )
        self._normalize_all_pushbutton = QtWidgets.QPushButton("Normalize All")
        self._normalize_all_pushbutton.setToolTip(
            "Normalize all Weight Maps"
        )
        self._invert_pushbutton = QtWidgets.QPushButton("Invert Weight Map")
        self._invert_pushbutton.setToolTip(
            "Invert the selected Weight Maps"
        )
        self._mirror_label = QtWidgets.QLabel("Mirror Axis:")
        self._mirror_combobox = QtWidgets.QComboBox()
        self._mirror_combobox.addItems([
            "topology",
            "world X",
            "world Y",
            "world Z",
            "object X",
            "object Y",
            "object Z",
        ])
        self._mirror_pushbutton = QtWidgets.QPushButton("Mirror Weight Map")
        self._mirror_pushbutton.setToolTip(
            "Mirror selected Weight Maps based on Mirror Axis or topology\n\n"
            "If mesh is not symmetrical, non symmetrical vertex weights will be set to 0"
        )
        self._combine_weightmaps_pushbutton = QtWidgets.QPushButton("Combine")
        self._combine_weightmaps_pushbutton.setToolTip(
            "Adds selected weight maps together\n\n"
            "First target delta is duplicated and new map is applied to duplicate"
        )
        self._subtract_weightmaps_pushbutton = QtWidgets.QPushButton("Subtract")
        self._subtract_weightmaps_pushbutton.setToolTip(
            "Subtracts selected weight maps from first selected weight map\n\n"
            "First target delta is duplicated and new map is applied to duplicate"
        )

        self._button_layout.addWidget(self._set_delta_weightmap_pushbutton, 0, 0, 1, 2)
        self._button_layout.addWidget(self._normalize_selected_pushbutton, 1, 0)
        self._button_layout.addWidget(self._normalize_all_pushbutton, 1, 1)
        self._button_layout.addWidget(self._combine_weightmaps_pushbutton, 2, 0)
        self._button_layout.addWidget(self._subtract_weightmaps_pushbutton, 2, 1)
        self._button_layout.addWidget(self._invert_pushbutton, 3, 0, 1, 2)
        self._button_layout.addWidget(self._mirror_label, 4, 0)
        self._button_layout.addWidget(self._mirror_combobox, 4, 1)
        self._button_layout.addWidget(self._mirror_pushbutton, 5, 0, 1, 2)

        self._normalize_selected_pushbutton.clicked.connect(self._on_normalize_selected_pushbutton_clicked)
        self._normalize_all_pushbutton.clicked.connect(self._on_normalize_all_pushbutton_clicked)
        self._invert_pushbutton.clicked.connect(self._on_invert_pushbutton_clicked)
        self._mirror_pushbutton.clicked.connect(self._on_mirror_pushbutton_clicked)
        self._combine_weightmaps_pushbutton.clicked.connect(self._on_combine_weightmaps_clicked)
        self._subtract_weightmaps_pushbutton.clicked.connect(self._on_subtract_weightmaps_clicked)
        self._set_delta_weightmap_pushbutton.clicked.connect(self._on_set_delta_weightmap_clicked)

        self._layout.addLayout(self._button_layout)

    def _populate_list_widget(self):
        # type: () -> None
        self._shape_listwidget.clear()
        if self.blendshape is None:
            return
        weight_maps = list_shapes(self.blendshape)
        if weight_maps:
            self._shape_listwidget.addItems(weight_maps)
        else:
            logger.warning(f"No weight maps found on {self.blendshape}...")

    def _on_blendshape_index_changed(self, blendshape):
        # type: (str) -> None
        self.blendshape = blendshape
        self._populate_list_widget()

    def _on_file_path_changed(self, file_path):
        # type: (str) -> None
        self.file_path = Path(file_path)

    def _on_normalize_selected_pushbutton_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        if not selected_maps:
            return
        weight_maps = [get_weights_from_blendshape_target(self.blendshape, x) for x in selected_maps]
        normalised_maps = WeightMap.normalize(weight_maps)
        for new_map, old_map in zip(normalised_maps, selected_maps):
            apply_weightmap_to_target(self.blendshape, old_map, new_map)

    def _on_normalize_all_pushbutton_clicked(self):
        # type: () -> None
        all_maps = get_weights_from_blendshape(self.blendshape)
        normalised_maps = WeightMap.normalize(all_maps)
        for new_map, old_map in zip(normalised_maps, all_maps):
            apply_weightmap_to_target(self.blendshape, old_map.name, new_map)

    def _on_invert_pushbutton_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        if not selected_maps:
            return
        for wm in selected_maps:
            inverse_target_weightmap(self.blendshape, wm)


    def _on_mirror_pushbutton_clicked(self):
        # type: () -> None
        selected_map = [x.text() for x in self._shape_listwidget.selectedItems()][0]
        if not selected_map:
            return
        if not self._mirror_combobox.currentText() == "topology":
            _mirror = self._mirror_combobox.currentText().split(" ")
            mirror_type = _mirror[0]
            mirror_axis = _mirror[1]
            
            mirror_weight_map_by_pos(self.blendshape, selected_map, mirror_type=mirror_type, mirror_axis=mirror_axis) 
        else:
            mirror_weight_map_by_topology_selection(self.blendshape, selected_map)


    def _on_combine_weightmaps_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        if not selected_maps:
            return
        combine_weight_maps(self.blendshape, selected_maps)
        self._shape_listwidget.clearSelection()
        self.REFRESH_SIGNAL.emit()

    def _on_subtract_weightmaps_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        if not selected_maps:
            return
        subtract_weight_maps(self.blendshape, selected_maps)
        self._shape_listwidget.clearSelection()
        self.REFRESH_SIGNAL.emit()

    def _on_set_delta_weightmap_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        if not selected_maps:
            return
        for wm in selected_maps:
            set_delta_weightmap_to_target(self.blendshape, wm)