from PySide2.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QMenu, QAction, QAbstractItemView
from PySide2.QtCore import Qt, QSignalBlocker
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from PySide2.QtCore import QPoint
    from PySide2.QtWidgets import QWidget

class FileTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super(FileTableWidget, self).__init__(parent)

        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["File Name", "File Size", "Date"])
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.setSortingEnabled(True)
        self.sortItems(0, Qt.DescendingOrder)
        self.sortItems(1, Qt.DescendingOrder)
        self.sortItems(2, Qt.DescendingOrder)

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QTableWidget.SingleSelection)
        self.setEditTriggers(QTableWidget.NoEditTriggers)

        self.horizontalHeader().setSortIndicator(0, Qt.DescendingOrder)
        self.verticalHeader().setVisible(False)

        self.context_menu = QMenu(self)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self.horizontalHeader().sortIndicatorChanged.connect(self.sort_all_columns)

    def add_file_entry(self, filename, creation_date, file_size):
        row_position = self.rowCount()
        self.insertRow(row_position)
        self.setItem(row_position, 0, QTableWidgetItem(filename))
        self.setItem(row_position, 1, QTableWidgetItem(creation_date))
        self.setItem(row_position, 2, QTableWidgetItem(file_size))

    def _show_context_menu(self, position):
        # type: (QPoint) -> None
        global_position = self.mapToGlobal(position)
        self.context_menu.exec_(global_position)

    def add_action(self, name, function):
        # type: (str, Any) -> None
        action = QAction(name, self)
        action.triggered.connect(function)
        self.context_menu.addAction(action)

    def sort_all_columns(self, logical_index, order):
        self.horizontalHeader().blockSignals(True)
        for col in range(self.columnCount()):
            self.sortByColumn(col, order)
        self.horizontalHeader().blockSignals(False)

