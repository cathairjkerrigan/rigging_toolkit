from typing import Optional, Type, TypeVar

from rigging_toolkit.core.filesystem import Path
import subprocess
from enum import Enum

from PySide2.QtCore import QPoint, Qt
from PySide2.QtGui import QColor, QTextCursor
from PySide2.QtWidgets import QAction, QMenu, QTextEdit, QWidget

T = TypeVar("T", bound=Enum)


class ProcessTextEdit(QTextEdit):
    def __init__(self, parent=None):
        # type: (Optional[QWidget]) -> None
        super(ProcessTextEdit, self).__init__(parent)

        self._history = []
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        self._clear_action = QAction("Clear Output", self)
        self._clear_action.triggered.connect(self.clear_history)
        self._open_selected_directory_action = QAction("Open Directory", self)
        self._open_selected_directory_action.triggered.connect(self._open_directory)

        self._textbox_menu = self.createStandardContextMenu()
        self._textbox_menu.addAction(self._clear_action)
        self._textbox_menu.addAction(self._open_selected_directory_action)

    def _check_indent(self):
        # type: () -> str
        """Check if text exists in textbox and add indent if True"""
        if not self._history:
            _indent = ""
        else:
            _indent = "<br />"

        return _indent

    def add_text(self, text):
        # type: (str) -> None
        """Update ProcessTextedit with history + new text"""
        color_text = '<span style=" font-size:7pt; font-weight:600; color:#######;" > {} </span>'.format(
            self._check_text(text)
        )
        _indent = self._check_indent()
        self._history.append(_indent + color_text)

        process_history_str = "".join(self._history)
        self.setText(process_history_str)
        self.moveCursor(QTextCursor.End)

    def add_warning(self, text):
        # type: (str) -> None
        color_text = '<span style=" font-size:7pt; font-weight:600; color:#f1ff00;" > {} </span>'.format(
            (">> " + self._check_text(text))
        )
        _indent = self._check_indent()
        self._history.append(_indent + color_text)

        process_history_str = "".join(self._history)
        self.setText(process_history_str)
        self.moveCursor(QTextCursor.End)

    def add_error(self, text):
        # type: (str) -> None
        color_text = '<span style=" font-size:7pt; font-weight:600; color:#ff3e3e;" > {} </span>'.format(
            (">> " + self._check_text(text))
        )
        _indent = self._check_indent()
        self._history.append(_indent + color_text)

        process_history_str = "".join(self._history)
        self.setText(process_history_str)
        self.moveCursor(QTextCursor.End)

    def add_success(self, text):
        # type: (str) -> None
        color_text = '<span style=" font-size:7pt; font-weight:600; color:#7CFC00;" > {} </span>'.format(
            (">> " + self._check_text(text))
        )
        _indent = self._check_indent()
        self._history.append(_indent + color_text)

        process_history_str = "".join(self._history)
        self.setText(process_history_str)
        self.moveCursor(QTextCursor.End)

    def add_info(self, text):
        # type: (str) -> None
        color_text = '<span style=" font-size:7pt; font-weight:600; color:#2ffdff;" > {} </span>'.format(
            (">> " + self._check_text(text))
        )
        _indent = self._check_indent()
        self._history.append(_indent + color_text)

        process_history_str = "".join(self._history)
        self.setText(process_history_str)
        self.moveCursor(QTextCursor.End)

    def clear_history(self):
        # type: (str) -> None
        """Clear ProcessTextedit"""
        self.clear()
        self._history = []

    def _check_text_selection(self):
        # type: () -> str
        """Return highlighted text from ProcessTextedit"""
        cursor = self.textCursor()
        cursor_text = cursor.selectedText()
        selected_text = cursor_text.replace("/", "\\")
        self._selected_directory = selected_text.encode("ascii", "ignore")

        return self._selected_directory

    def _open_directory(self):
        # type: () -> None
        """Open file directory using windows explorer"""
        self._check_text_selection()
        subprocess.call("explorer {}".format(self._selected_directory), shell=True)

    def _show_context_menu(self, point):
        # type: (QPoint) -> None
        """Show context menu and check if selected text is directory"""
        self._check_text_selection()
        context_menu = QMenu()
        context_menu.addAction(self._clear_action)
        if Path(self._selected_directory).is_dir():
            context_menu.addSeparator()
            context_menu.addAction(self._open_selected_directory_action)

        context_menu.exec_(self.mapToGlobal(point))

    def _check_text(self, text):
        # type: (str) -> str
        if "\n" in text:
            check_text = text.replace("\n", "<br />")
        else:
            check_text = text
        return check_text
