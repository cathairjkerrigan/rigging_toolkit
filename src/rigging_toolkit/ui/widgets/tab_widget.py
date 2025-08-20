from PySide2.QtWidgets import QWidget
from typing import Optional

from rigging_toolkit.core.context import Context

class TabWidget(QWidget):
    TAB_NAME = "Tab Name"

    def __init__(self):
        pass

    def _on_context_changed(self, context):
        # type: (Optional[Context]) -> None
        self.context = context