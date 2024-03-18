from PySide2 import QtWidgets, QtCore, QtGui
from rigging_toolkit.core import Context
import logging
from rigging_toolkit.core.filesystem import Path
from typing import Optional

logger = logging.getLogger(__name__)

class CreateSeriesDialog(QtWidgets.QDialog):

    def __init__(self, path, current_series, parent=None):
        # type: (Path, int, Optional[str]) -> None

        super(CreateSeriesDialog, self).__init__(parent=parent)

        self._path = path

        self._current_series = current_series

        self.setWindowTitle(f"Create New {path.name} Series")

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        self._series_label = QtWidgets.QLabel("New Series: ")
        regexp = QtCore.QRegExp("^[0-9][0-9][0-9]$")
        validator = QtGui.QRegExpValidator(regexp)
        next_series = self._current_series + 1
        self._series_lineedit = QtWidgets.QLineEdit(str(next_series))
        self._series_lineedit.setValidator(validator)
        self._status_label = QtWidgets.QLabel("Status: ")
        folder_to_create = self._path / self._series_lineedit.text()
        self._status = QtWidgets.QLabel(str(folder_to_create))
        self._status.setStyleSheet("color: white;")
        
        self._accept_pushbutton = QtWidgets.QPushButton("Create")
        self._accept_pushbutton.setDisabled(False)
        self._cancel_pushbutton = QtWidgets.QPushButton("Cancel")

    def create_layouts(self):

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        series_layout = QtWidgets.QHBoxLayout()
        series_layout.addWidget(self._series_label)
        series_layout.addWidget(self._series_lineedit)

        status_layout = QtWidgets.QHBoxLayout()
        status_layout.addWidget(self._status_label)
        status_layout.addWidget(self._status)
        status_layout.addStretch()

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._accept_pushbutton)
        button_layout.addWidget(self._cancel_pushbutton)

        main_layout.addLayout(series_layout)
        main_layout.addLayout(status_layout)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self._series_lineedit.textChanged.connect(self._on_series_changed)
        self._accept_pushbutton.clicked.connect(self.create_new_series)
        self._cancel_pushbutton.clicked.connect(self.close)

    def create_new_series(self):
        folder = self._path / self._series_lineedit.text()
        folder.mkdir(parents=True)
        self.close()

    def _on_series_changed(self):
        if self._series_lineedit.hasAcceptableInput():
            folder_to_create = self._path / self._series_lineedit.text()
            if not folder_to_create.exists():
                self._status.setStyleSheet("color: white")
                self._status.setText(str(folder_to_create))
                self._accept_pushbutton.setDisabled(False)
            else:
                self._accept_pushbutton.setDisabled(True)
                self._status.setStyleSheet("color: orange")
                self._status.setText(f"Series {self._series_lineedit.text()} already exists")

        else:
            self._accept_pushbutton.setDisabled(True)
            self._status.setStyleSheet("color: orange")
            self._status.setText("Series should be three consequtive digits")

    @property
    def value(self):
        return (int(self._series_lineedit.text()))
