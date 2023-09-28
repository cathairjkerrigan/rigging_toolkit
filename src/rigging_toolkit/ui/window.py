from PySide2 import QtWidgets

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from rigging_toolkit.maya.utils import toggle_template_display_for_all_meshes

import logging

from shiboken2 import getCppPointer

logger = logging.getLogger(__name__)


class RiggingToolboxWindow(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    
    WINDOW_TITLE = "Rigging Toolbox"

    _instance = None

    @classmethod
    def open(cls):
        if cls._instance is None:
            cls._instance = cls()

        cls._instance.show(dockable=True)

    def __init__(self):
        super(RiggingToolboxWindow, self).__init__()

        self.setWindowTitle(self.WINDOW_TITLE)

        self._layout = QtWidgets.QVBoxLayout()
        
        self.setLayout(self._layout)

        self.test_button = QtWidgets.QPushButton("Test Button")

        self._layout.addWidget(self.test_button)

        self.test_button.clicked.connect(self.test_func)

    def test_func(self):
        logger.info("Button test")
        toggle_template_display_for_all_meshes()