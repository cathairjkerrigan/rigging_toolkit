from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets, QtCore
from rigging_toolkit.maya.utils import list_shapes, export_weight_map, export_all_weight_maps
import logging
from rigging_toolkit.core.filesystem import Path

logger = logging.getLogger(__name__)

class ExportWeightMapTab(TabWidget):
    TAB_NAME = "Export Weight Maps"
    EXPORT_SIGNAL = QtCore.Signal()

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

        self._export_selected_button = QtWidgets.QPushButton("Export Selected")
        self._export_all_button = QtWidgets.QPushButton("Export All")

        self._button_layout.addWidget(self._export_selected_button)
        self._button_layout.addWidget(self._export_all_button)

        self._export_selected_button.clicked.connect(self._on_export_selected_button_clicked)
        self._export_all_button.clicked.connect(self._export_all_button_clicked)

        self._layout.addLayout(self._button_layout)

    def _populate_list_widget(self):
        # type: () -> None
        self._shape_listwidget.clear()
        if self.blendshape is None:
            return
        shapes = list_shapes(self.blendshape)
        if shapes:
            self._shape_listwidget.addItems(shapes)
        else:
            logger.warning(f"No adjusted weight maps found on {self.blendshape}...")

    def _on_blendshape_index_changed(self, blendshape):
        # type: (str) -> None
        self.blendshape = blendshape
        if not self.blendshape:
            return
        self._populate_list_widget()

    def _on_file_path_changed(self, file_path):
        # type: (str) -> None
        self.file_path = Path(file_path)

    def _on_export_selected_button_clicked(self):
        # type: () -> None
        selected_maps = [x.text() for x in self._shape_listwidget.selectedItems()]
        for wm in selected_maps:
            export_weight_map(self.blendshape, wm, Path(self.file_path))

        self.EXPORT_SIGNAL.emit()

    def _export_all_button_clicked(self):
        # type: () -> None
        export_all_weight_maps(self.blendshape, Path(self.file_path))
        self.EXPORT_SIGNAL.emit()
