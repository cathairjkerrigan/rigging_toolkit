from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets, QtCore
from rigging_toolkit.maya.utils import list_shapes, import_weight_map
from rigging_toolkit.core.filesystem import find_all_latest, find_latest
import logging

logger = logging.getLogger(__name__)

class ImportWeightMapTab(TabWidget):
    TAB_NAME = "Import Weight Maps"
    IMPORT_SIGNAL = QtCore.Signal()

    def __init__(self, parent=None, file_path=None, blendshape=None):
        super(TabWidget, self).__init__(parent=parent)
        self.blendshape = blendshape
        self.file_path = file_path
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self._listwidget_layout = QtWidgets.QHBoxLayout()

        self._map_listwidget = QtWidgets.QListWidget()

        self._shape_listwidget = QtWidgets.QListWidget()
        self._shape_listwidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self._populate_shape_list_widget()
        self._populate_map_list_widget()
        self._listwidget_layout.addWidget(self._map_listwidget)
        self._listwidget_layout.addWidget(self._shape_listwidget)
        self._layout.addLayout(self._listwidget_layout)

        self._button_layout = QtWidgets.QHBoxLayout()
        self._button_layout.addStretch()

        self._import_by_name = QtWidgets.QPushButton("Import By Name")
        self._import_selected_button = QtWidgets.QPushButton("Import To Selected")
        self._import_all_button = QtWidgets.QPushButton("Import To All")

        self._button_layout.addWidget(self._import_by_name)
        self._button_layout.addWidget(self._import_selected_button)
        self._button_layout.addWidget(self._import_all_button)

        self._import_by_name.clicked.connect(self._on_import_by_name_clicked)
        self._import_selected_button.clicked.connect(self._on_import_selected_clicked)
        self._import_all_button.clicked.connect(self._on_import_all_clicked)

        self._layout.addLayout(self._button_layout)

    def _populate_shape_list_widget(self):
        # type: () -> None
        self._shape_listwidget.clear()
        shapes = list_shapes(self.blendshape)
        if shapes:
            self._shape_listwidget.addItems(shapes)

    def _populate_map_list_widget(self):
        # type: () -> None
        self._map_listwidget.clear()
        weight_map_files = find_all_latest(self.file_path, "wmap")
        if weight_map_files:
            self._map_listwidget.addItems([x.stem.split(".")[0] for x in weight_map_files])

    def _on_blendshape_index_changed(self, blendshape):
        # type: (str) -> None
        self.blendshape = blendshape
        self._populate_shape_list_widget()

    def _on_file_path_changed(self, file_path):
        # type: (str) -> None
        self.file_path = file_path
        self._populate_map_list_widget()

    def _on_import_by_name_clicked(self):
        # type: () -> None
        shapes = list_shapes(self.blendshape)
        if not shapes:
            return
        weight_map_files = find_all_latest(self.file_path, "wmap")
        
        for wm in weight_map_files:
            name = wm.stem.split(".")[0] # remove versioning to compare names
            if not name in shapes:
                continue
            import_weight_map(self.blendshape, name, wm)

        self.IMPORT_SIGNAL.emit()

    def _on_import_selected_clicked(self):
        # type: () -> None
        current_selected_wm = self._map_listwidget.currentItem().text()
        current_selected_shapes = [x.text() for x in self._shape_listwidget.selectedItems()]

        latest_wm, _ = find_latest(self.file_path, current_selected_wm, "wmap")

        for shape in current_selected_shapes:
            import_weight_map(self.blendshape, shape, latest_wm)

        self.IMPORT_SIGNAL.emit()

    def _on_import_all_clicked(self):
        # type: () -> None
        current_selected_wm = self._map_listwidget.currentItem().text()
        shapes = list_shapes(self.blendshape)

        latest_wm, _ = find_latest(self.file_path, current_selected_wm, "wmap")

        for shape in shapes:
            import_weight_map(self.blendshape, shape, latest_wm)

        self.IMPORT_SIGNAL.emit()