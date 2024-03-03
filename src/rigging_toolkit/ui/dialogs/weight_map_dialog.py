from PySide2 import QtWidgets, QtGui
from rigging_toolkit.core import Context, validate_path
import logging
from typing import Optional
from rigging_toolkit.ui.tabs.weight_maps import ExportWeightMapTab, ImportWeightMapTab, WeightMapUtilsTab
from rigging_toolkit.ui.widgets import TabWidget
from rigging_toolkit.maya.utils import get_all_blendshapes

logger = logging.getLogger(__name__)

class WeightMapTool(QtWidgets.QDialog):

    def __init__(self, context=None, parent=None):
        # type: (Optional[Context], Optional[QtWidgets.QWidget]) -> None

        super(WeightMapTool, self).__init__(parent=parent)

        self.setWindowTitle("Weight Map Tool")

        self.context = context

        self._initial_directory = validate_path(context.utilities_path / "masks", create_missing=True)

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self.child_widgets = []

        self._button_layout = QtWidgets.QGridLayout()

        self._dir_label = QtWidgets.QLabel("File Path: ")
        self._dir_lineedit = QtWidgets.QLineEdit()
        self._dir_lineedit.setText(str(self._initial_directory))
        self._dir_pushbutton = QtWidgets.QPushButton()
        self._dir_pushbutton.setIcon(QtGui.QIcon(":fileOpen.png"))
        self._refresh_pushbutton = QtWidgets.QPushButton("Refresh")

        self._button_layout.addWidget(self._dir_label, 0, 0)
        self._button_layout.addWidget(self._dir_lineedit, 0, 1)
        self._button_layout.addWidget(self._dir_pushbutton, 0, 2)

        self._blendshape_label = QtWidgets.QLabel("Blendshape: ")
        self._blendshape_combobox = QtWidgets.QComboBox()

        self._button_layout.addWidget(self._blendshape_label, 1, 0)
        self._button_layout.addWidget(self._blendshape_combobox, 1, 1)
        self._button_layout.addWidget(self._refresh_pushbutton, 1, 2)

        self._layout.addLayout(self._button_layout)

        self._tab_widget = QtWidgets.QTabWidget()
        self._layout.addWidget(self._tab_widget)

        self._export_weights_tab = ExportWeightMapTab()
        self.add_tab(self._tab_widget, self._export_weights_tab)

        self._import_weights_tab = ImportWeightMapTab()
        self.add_tab(self._tab_widget, self._import_weights_tab)
        self._export_weights_tab.EXPORT_SIGNAL.connect(self._import_weights_tab._populate_map_list_widget)

        self._normalize_weights_tab = WeightMapUtilsTab()
        self.add_tab(self._tab_widget, self._normalize_weights_tab)

        self._import_weights_tab.IMPORT_SIGNAL.connect(self._export_weights_tab._populate_list_widget)
        self._import_weights_tab.IMPORT_SIGNAL.connect(self._normalize_weights_tab._populate_list_widget)
        self._refresh_pushbutton.clicked.connect(self.populate_blendshape_combobox)

        self.populate_blendshape_combobox()
        self.update_children_file_path()

    def add_tab(self, tab_widget, child_widget):
        # type: (QtWidgets.QTabWidget, TabWidget) -> None
        self._dir_lineedit.textChanged.connect(self.update_children_file_path)
        self._blendshape_combobox.currentIndexChanged.connect(self.update_children_combobox)
        tab_widget.addTab(child_widget, child_widget.TAB_NAME)
        self.child_widgets.append(child_widget)

    def update_children_file_path(self):
        # type: () -> None
        for widget in self.child_widgets:
            widget._on_file_path_changed(self._dir_lineedit.text())
        
    def update_children_combobox(self):
        # type: () -> None
        for widget in self.child_widgets:
            widget._on_blendshape_index_changed(self._blendshape_combobox.currentText())

    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context

    def open_dir(self):
        # type: () -> None
        previous_path = self._dir_lineedit.text()
        assetDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory", self.initial_directory)
        if assetDir == "":
            self._dir_lineedit.setText(previous_path)
            self.initial_directory = previous_path
        else:
            self._dir_lineedit.setText(assetDir)
            self.initial_directory = assetDir

    def populate_blendshape_combobox(self):
        # type: () -> None
        blendshapes = get_all_blendshapes()
        self._blendshape_combobox.addItems(blendshapes)
        self.update_children_combobox()

