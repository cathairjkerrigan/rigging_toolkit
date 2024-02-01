from typing import Any, List, Optional, Tuple
from PySide2.QtCore import Slot
from PySide2.QtWidgets import QMessageBox, QWidget


class MultiMessageBox(QMessageBox):
    def __init__(self, parent=None):
        # type: (Optional[QWidget]) -> None
        super(MultiMessageBox, self).__init__(parent)
        self.button_objects = {}

    def setup(self, title, message, buttons):
        # type: (str, str, List[Tuple[str, Any]]) -> None

        for button in self.buttons():
            self.removeButton(button)

        self.button_objects.clear()
        self.setWindowTitle(title)
        self.setText(message)

        for button_text, return_value in buttons:
            button = self.addButton(button_text, QMessageBox.YesRole)
            self.button_objects[button] = return_value

        self.addButton(QMessageBox.Cancel)

    @Slot()
    def exec_(self):
        # type: () -> Optional[Any]
        super(MultiMessageBox, self).exec_()

        clicked_button = self.clickedButton()
        if clicked_button in self.button_objects:
            return self.button_objects[clicked_button]
        else:
            return None
