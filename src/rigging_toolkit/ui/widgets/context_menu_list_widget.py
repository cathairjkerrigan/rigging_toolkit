from typing import TYPE_CHECKING, Any, List, Optional

from PySide2.QtCore import Qt
from PySide2.QtWidgets import QAction, QListWidget, QMenu

if TYPE_CHECKING:
    from PySide2.QtCore import QPoint
    from PySide2.QtWidgets import QWidget

class ContextMenuListWidget(QListWidget):
    def __init__(self, parent=None):
        # type: (Optional[QWidget]) -> None
        super(ContextMenuListWidget, self).__init__(parent)

        # Create context menu
        self.context_menu = QMenu(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _show_context_menu(self, position):
        # type: (QPoint) -> None
        global_position = self.mapToGlobal(position)
        self.context_menu.exec_(global_position)

    def add_action(self, name, function):
        # type: (str, Any) -> None
        action = QAction(name, self)
        action.triggered.connect(function)
        self.context_menu.addAction(action)

    def get_selection(self):
        # type: () -> List[str]
        return [x.text() for x in self.selectedItems()]
