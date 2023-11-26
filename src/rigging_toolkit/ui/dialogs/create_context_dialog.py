from PySide2 import QtWidgets
from rigging_toolkit.core import Context
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

class CreateContextDialog(QtWidgets.QDialog):

    def __init__(self, path, parent=None):
        # type: (Path, Optional[str]) -> None

        super(CreateContextDialog, self).__init__(parent=parent)

        self._path = path

        self._new_context = None

        self.setWindowTitle("Create New Character")

        self.setMinimumWidth(300)

        self.create_widgets()
        self.create_layouts()
        self.create_connections()

    def create_widgets(self):
        self._char_label = QtWidgets.QLabel("New Character: ")
        self._char_lineedit = QtWidgets.QLineEdit()
        
        self._accept_pushbutton = QtWidgets.QPushButton("Create")
        self._cancel_pushbutton = QtWidgets.QPushButton("Cancel")

    def create_layouts(self):

        main_layout = QtWidgets.QVBoxLayout()
        self.setLayout(main_layout)

        char_layout = QtWidgets.QHBoxLayout()
        char_layout.addWidget(self._char_label)
        char_layout.addWidget(self._char_lineedit)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._accept_pushbutton)
        button_layout.addWidget(self._cancel_pushbutton)

        main_layout.addLayout(char_layout)
        main_layout.addLayout(button_layout)

    def create_connections(self):
        self._accept_pushbutton.clicked.connect(self.create_new_context)
        self._cancel_pushbutton.clicked.connect(self.close)

    def create_new_context(self):
        name = self._char_lineedit.text()
        if name == "" or name is None:
            logger.warning("No name passed, cannot create context...")
            return

        new_context = Context.new(
            project_path=self._path,
            character_name=name,
            create_context=True
        )

        if new_context.is_valid:
            self._new_context = new_context

        self.close()

    @property
    def name(self):
        return self._char_lineedit.text()
    
    @property
    def new_context(self):
        return self._new_context