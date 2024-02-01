from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets, QtCore
from rigging_toolkit.maya.utils import get_adjusted_weight_maps, normalize_weight_maps, normalize_default_weight_maps
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class NormalizeWeightMapTab(TabWidget):
    TAB_NAME = "Normalize Weight Maps"

    def __init__(self, parent=None, file_path=None, blendshape=None):
        super(TabWidget, self).__init__(parent=parent)
        self.blendshape = blendshape
        self.file_path = file_path
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self._shape_listwidget = QtWidgets.QListWidget()
        self._shape_listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._populate_list_widget()
        self._layout.addWidget(self._shape_listwidget)

        self._button_layout = QtWidgets.QHBoxLayout()
        self._button_layout.addStretch()

        self._normalize_default_pushbutton = QtWidgets.QPushButton("Normalize Default")
        self._normalize_selected_pushbutton = QtWidgets.QPushButton("Normalize Selected")
        self._normalize_all_pushbutton = QtWidgets.QPushButton("Normalize All")

        self._button_layout.addWidget(self._normalize_default_pushbutton)
        self._button_layout.addWidget(self._normalize_selected_pushbutton)
        self._button_layout.addWidget(self._normalize_all_pushbutton)

        self._normalize_default_pushbutton.clicked.connect(self._on_normalize_default_pushbutton_clicked)
        self._normalize_selected_pushbutton.clicked.connect(self._on_normalize_selected_pushbutton_clicked)
        self._normalize_all_pushbutton.clicked.connect(self._on_normalize_all_pushbutton_clicked)

        self._layout.addLayout(self._button_layout)

    def _populate_list_widget(self):
        # type: () -> None
        self._shape_listwidget.clear()
        if self.blendshape is None:
            return
        weight_maps = get_adjusted_weight_maps(self.blendshape)
        if weight_maps:
            self._shape_listwidget.addItems(weight_maps)
        else:
            logger.warning(f"No adjusted weight maps found on {self.blendshape}...")

    def _on_blendshape_index_changed(self, blendshape):
        # type: (str) -> None
        self.blendshape = blendshape
        self._populate_list_widget()

    def _on_file_path_changed(self, file_path):
        # type: (str) -> None
        self.file_path = Path(file_path)

    def _on_normalize_default_pushbutton_clicked(self):
        # type: () -> None
        normalize_default_weight_maps(self.blendshape)

    def _on_normalize_selected_pushbutton_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        normalize_weight_maps(self.blendshape, selected_maps)

    def _on_normalize_all_pushbutton_clicked(self):
        # type: () -> None
        all_maps = [x.text() for x in self._shape_listwidget.items()]
        normalize_weight_maps(self.blendshape, all_maps)
