from PySide2 import QtWidgets, QtGui, QtCore
from maya import cmds
from pathlib import Path
import json
from rigging_toolkit.core import path_exists, get_folders, Context, validate_path
import logging
from typing import Optional, Generator, cast
import re
import os
from rigging_toolkit.ui.dialogs import CreateContextDialog, CreateSeriesDialog

import contextlib

logger = logging.getLogger(__name__)

class ContextUI(QtWidgets.QGroupBox):

    IGNORE_LIST = [".config"]

    context_changed = QtCore.Signal(Context)

    def __init__(self, parent=None, enable_new=True):
        super(ContextUI, self).__init__(parent=parent)

        self._enable_new = enable_new

        self.initial_directory = cmds.internalVar(userPrefDir=True)

        self._suppress_context_changed_counter = 0

        self._context = None # type: Context

        self.context_changed.connect(lambda x: logger.debug(f"context_changed to {str(x)}"))
        
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.load_settings()
        
    @property
    def suppress_context_changed_signal(self):
        # type: () -> bool
        return self._suppress_context_changed_counter < 0
    
    @suppress_context_changed_signal.setter
    def suppress_context_changed_signal(self, value):
        # type: (bool) -> None
        if value:
            self._suppress_context_changed_counter -= 1
        else:
            self._suppress_context_changed_counter += 1

    @property
    def context(self):
        # type: () -> Optional[Context]
        return self._context
    
    @context.setter
    def context(self, value):
        # type: (Optional[Context]) -> None
        if not self.suppress_context_changed_signal:
            if self._context != value:
                self._context = value
                self.context_changed.emit(self._context)

    @contextlib.contextmanager
    def prevent_context_changed_event(self):
        # type: () -> Generator[None, None, None]
        '''
        Should be used with a "with" statement to prevent context changed event from being raised
        '''

        try:
            self.suppress_context_changed_signal = True
            yield
        except Exception as e:
            logger.exception(e)
            raise

        finally:
            self.suppress_context_changed_signal = False


    def create_widgets(self):
        self._dir_label = QtWidgets.QLabel("Project Path: ")
        self._dir_lineedit = QtWidgets.QLineEdit()
        self._dir_pushbutton = QtWidgets.QPushButton()
        self._dir_pushbutton.setIcon(QtGui.QIcon(":fileOpen.png"))

        self._char_label = QtWidgets.QLabel("Character: ")

        self._char_combobox = QtWidgets.QComboBox()

        self._assets_pushbutton = QtWidgets.QPushButton("Assets")
        self._assets_combobox = QtWidgets.QComboBox()

        self._rigs_pushbutton = QtWidgets.QPushButton("Rigs")
        self._rigs_combobox = QtWidgets.QComboBox()

        self._shaders_pushbutton = QtWidgets.QPushButton("Shaders")
        self._shaders_combobox = QtWidgets.QComboBox()

        self._shapes_pushbutton = QtWidgets.QPushButton("Shapes")
        self._shapes_combobox = QtWidgets.QComboBox()

        self._texture_pushbutton = QtWidgets.QPushButton("Textures")
        self._texture_combobox = QtWidgets.QComboBox()

        self._utilities_pushbutton = QtWidgets.QPushButton("Utilities")
        self._utilities_combobox = QtWidgets.QComboBox()

    def create_layouts(self):
        layout = QtWidgets.QVBoxLayout()

        self.setLayout(layout)

        dir_layout = QtWidgets.QHBoxLayout()
        dir_layout.addWidget(self._dir_label)
        dir_layout.addWidget(self._dir_lineedit)
        dir_layout.addWidget(self._dir_pushbutton)

        char_layout = QtWidgets.QGridLayout()
        char_layout.addWidget(self._char_label, 0, 0)
        char_layout.addWidget(self._char_combobox, 0, 2)

        series_groupbox = QtWidgets.QGroupBox("Series")

        series_groupbox.setStyleSheet(
            """
            QGroupBox {
                border: 2px solid gray;
                border-radius: 5px;
                margin-top: 1ex; /* leave space at the top for the title */
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; /* position at the top center */
                margin: 0 2ex;
                left: 2ex;
            }
            """
        )

        series_groupbox_layout = QtWidgets.QVBoxLayout()

        series_groupbox.setLayout(series_groupbox_layout)

        series_top_layout = QtWidgets.QHBoxLayout()
        series_top_layout.addWidget(self._assets_pushbutton)
        series_top_layout.addWidget(self._assets_combobox)
        series_top_layout.addWidget(self._rigs_pushbutton)
        series_top_layout.addWidget(self._rigs_combobox)
        series_top_layout.addWidget(self._shaders_pushbutton)
        series_top_layout.addWidget(self._shaders_combobox)

        series_bot_layout = QtWidgets.QHBoxLayout()
        series_bot_layout.addWidget(self._shapes_pushbutton)
        series_bot_layout.addWidget(self._shapes_combobox)
        series_bot_layout.addWidget(self._texture_pushbutton)
        series_bot_layout.addWidget(self._texture_combobox)
        series_bot_layout.addWidget(self._utilities_pushbutton)
        series_bot_layout.addWidget(self._utilities_combobox)

        series_groupbox_layout.addLayout(series_top_layout)
        series_groupbox_layout.addLayout(series_bot_layout)

        layout.addLayout(dir_layout)
        layout.addLayout(char_layout)
        layout.addWidget(series_groupbox)
        # layout.addLayout(series_top_layout)
        # layout.addLayout(series_bot_layout)

        layout.addStretch()

    def create_connections(self):
        self._dir_pushbutton.clicked.connect(self.open_dir)
        self._dir_lineedit.textChanged.connect(self.load_project_path)
        self._char_combobox.currentIndexChanged.connect(self.load_character_name)
        self._assets_pushbutton.clicked.connect(self._open_assets_series_folder)
        self._rigs_pushbutton.clicked.connect(self._open_rigs_series_folder)
        self._shaders_pushbutton.clicked.connect(self._open_shaders_series_folder)
        self._shapes_pushbutton.clicked.connect(self._open_shapes_series_folder)
        self._texture_pushbutton.clicked.connect(self._open_texture_series_folder)
        self._utilities_pushbutton.clicked.connect(self._open_utilities_series_folder)

        self._assets_combobox.currentIndexChanged.connect(self._on_series_changed)
        self._rigs_combobox.currentIndexChanged.connect(self._on_series_changed)
        self._shaders_combobox.currentIndexChanged.connect(self._on_series_changed)
        self._shapes_combobox.currentIndexChanged.connect(self._on_series_changed)
        self._texture_combobox.currentIndexChanged.connect(self._on_series_changed)
        self._utilities_combobox.currentIndexChanged.connect(self._on_series_changed)

    def reset_series_state(self):
        self.reset_assets()
        self.reset_rigs()
        self.reset_shaders()
        self.reset_shapes()
        self.reset_texture()
        self.reset_utilities()

    def reset_assets(self):
        self._assets_combobox.clear()
        self._assets_combobox.setDisabled(True)
        self._assets_pushbutton.setDisabled(True)

    def reset_rigs(self):
        self._rigs_combobox.clear()
        self._rigs_combobox.setDisabled(True)
        self._rigs_pushbutton.setDisabled(True)

    def reset_shaders(self):
        self._shaders_combobox.clear()
        self._shaders_combobox.setDisabled(True)
        self._shaders_pushbutton.setDisabled(True)

    def reset_shapes(self):
        self._shapes_combobox.clear()
        self._shapes_combobox.setDisabled(True)
        self._shapes_combobox.setDisabled(True)

    def reset_texture(self):
        self._texture_combobox.clear()
        self._texture_combobox.setDisabled(True)
        self._texture_pushbutton.setDisabled(True)

    def reset_utilities(self):
        self._utilities_combobox.clear()
        self._utilities_combobox.setDisabled(True)
        self._texture_pushbutton.setDisabled(True)

    def open_dir(self):
        previous_path = self._dir_lineedit.text()
        assetDir = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Directory", self.initial_directory)
        if assetDir == "":
            self._dir_lineedit.setText(previous_path)
            self.initial_directory = previous_path
        else:
            self._dir_lineedit.setText(assetDir)
            self.initial_directory = assetDir

    def save_settings(self):
        settings_path = Path(__file__).resolve().parent / "context_settings.json"
        settings = {}
        settings["project_path"] = self._dir_lineedit.text()
        settings["index"] = self._char_combobox.currentIndex()

        with open(str(settings_path), "w") as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        settings_path = Path(__file__).resolve().parent / "context_settings.json"
        with open(str(settings_path), "r") as f:
            settings = json.load(f)

        file_path = settings["project_path"]
        character_index = settings["index"]

        self._dir_lineedit.setText(file_path)
        self._char_combobox.setCurrentIndex(character_index)

        self.load_context()

    def reset_character_combobox(self):
        self._char_combobox.clear()
        self._char_combobox.setDisabled(True)

    def set_character_names(self):
        self.reset_character_combobox()
        if not self.project_path():
            return
        for folder in get_folders(self.project_path(), ignore_list=self.IGNORE_LIST):
            self._char_combobox.addItem(folder.name)

        self._char_combobox.addItem("new...")
        self._char_combobox.setDisabled(False)


    def load_project_path(self):
        with self.prevent_context_changed_event():
            if self._dir_lineedit.text() and path_exists(self._dir_lineedit.text()):
                self.reset_character_combobox()
                self.set_character_names()
                self._char_combobox.setDisabled(False)

        self.context = self.update_context()

    def load_character_name(self):
        with self.prevent_context_changed_event():
            if self.character_name() is None:
                self.reset_series_state()
                self.update_context()
                return
            if not self.project_path():
                self.reset_series_state()
                self.update_context()
                return
            
            if self._char_combobox.currentText() == "new..." and self.context:
                folder = self.context.project_path
                previous_character = self.context.character_name

                self._char_combobox.setCurrentText(previous_character)
                dialog = CreateContextDialog(folder)
                dialog.exec_()
                self.set_character_names()
                self._char_combobox.setCurrentText(dialog.name)

            character_path = self.project_path() / self.character_name()
            if path_exists(character_path):
                context = Context.new(
                    self.project_path(),
                    self.character_name()
                )
                if context.is_valid:
                    self.update_series("assets", context)
                    self.update_series("rigs", context)
                    self.update_series("shaders", context)
                    self.update_series("shapes", context)
                    self.update_series("texture", context)
                    self.update_series("utilities", context)
                else:
                    self.reset_series_state()
            else:
                self.reset_series_state()

        self.context = self.update_context()

    def load_context(self):
        path = self._dir_lineedit.text()
        name = self._char_combobox.currentText()
        if not path_exists(path) or name == "":
            return
        self.context = self.initialize_context(path, name)

        self.load_series(self.context)

    def initialize_context(self, path, name):
        context = Context.new(
            project_path=Path(path),
            character_name=name,
            create_context=False
        )

        return context
    
    def update_context(self):
        context = Context(
            project_path=self.project_path(),
            character_name=self.character_name(),
            assets_series=self.assets_series(),
            rigs_series=self.rigs_series(),
            texture_series=self.textures_series(),
            shaders_series=self.shaders_series(),
            shapes_series=self.shapes_series(),
            utilities_series=self.utilities_series(),
            animation_series=self.animation_series(),
            build_series=self.build_series(),
            config_path=self.config_path()
        )

        if context.is_valid:
            return context
        
        return None

    def project_path(self):
        if self._dir_lineedit.text() == "" or not path_exists(self._dir_lineedit.text()):
            return None
        return Path(self._dir_lineedit.text())
    
    def character_name(self):
        if self._char_combobox.currentText() != "":
            return self._char_combobox.currentText()
        else:
            return None
    
    def assets_series(self):
        try:
            return int(self._assets_combobox.currentText())
        except ValueError:
            return -1
        
    def rigs_series(self):
        try:
            return int(self._rigs_combobox.currentText())
        except ValueError:
            return -1
        
    def textures_series(self):
        try:
            return int(self._texture_combobox.currentText())
        except ValueError:
            return -1

    def shaders_series(self):
        try:
            return int(self._shaders_combobox.currentText())
        except ValueError:
            return -1

    def shapes_series(self):
        try:
            return int(self._shapes_combobox.currentText())
        except ValueError:
            return -1

    def utilities_series(self):
        try:
            return int(self._utilities_combobox.currentText())
        except ValueError:
            return -1

    def animation_series(self):
        project_path = self.project_path()
        if project_path is None:
            return
        character_name = self.character_name()
        if character_name is None:
            return
        series_match = re.compile("\d\d\d")

        animation_path = project_path / character_name / "animation"

        if not path_exists(animation_path):
            return -1

        series = [
            f.name for f in animation_path.iterdir() if series_match.match(f.name)
        ]
        
        if not series:
            return -1
        
        return max(map(int, series))

    def build_series(self):
        project_path = self.project_path()
        if project_path is None:
            return
        character_name = self.character_name()
        if character_name is None:
            return
        series_match = re.compile("\d\d\d")

        builds_path = project_path / character_name / "builds"

        if not path_exists(builds_path):
            return -1

        series = [
            f.name for f in builds_path.iterdir() if series_match.match(f.name)
        ]
        
        if not series:
            return -1
        
        return max(map(int, series))

    def config_path(self):
        project_path = self.project_path()
        if project_path is None:
            return
        character_name = self.character_name()
        if character_name is None:
            return

        config_path = project_path / character_name / "wip" / ".config"

        if not path_exists(config_path):
            return None

        return config_path
    
    def load_series(self, context):
        self.update_series("assets", context)
        self.update_series("rigs", context)
        self.update_series("shaders", context)
        self.update_series("shapes", context)
        self.update_series("texture", context)
        self.update_series("utilities", context)

    def update_series(self, name, context):

        series_button = getattr(self, f"_{name}_pushbutton") # type: QtWidgets.QPushButton

        series_button.setDisabled(True)

        series_combobox = getattr(self, f"_{name}_combobox") # type: QtWidgets.QComboBox

        series_combobox.setDisabled(True)
        series_combobox.clear()

        latest_series = getattr(context, f"{name}_series")
        series_path = getattr(context, f"{name}_path")
        if series_path:
            series_parent_folder = getattr(context, f"{name}_path").parent
            series_parent_folder = validate_path(series_parent_folder)

            all_series = [x.name for x in series_parent_folder.iterdir() if x.is_dir()]

            if all_series:
                series_button.setDisabled(False)
                series_combobox.addItems(all_series)
                if self._enable_new:
                    series_combobox.insertSeparator(series_combobox.count())
                    series_combobox.addItem("new...")
                
                series_combobox.setCurrentText(f"{latest_series:03d}")
                series_combobox.setDisabled(False)

    def _on_series_changed(self):
        sender = cast(QtWidgets.QComboBox, self.sender())

        if sender.currentText() == "new...":
            folder = None
            previous_value = -1

            if sender is self._assets_combobox:
                folder = self.context.assets_path if self.context else None
                previous_value = self.context.assets_series if self.context else -1
            elif sender is self._rigs_combobox:
                folder = self.context.rigs_path if self.context else None
                previous_value = self.context.rigs_series if self.context else -1
            elif sender is self._shaders_combobox:
                folder = self.context.shaders_path if self.context else None
                previous_value = self.context.shaders_series if self.context else -1
            elif sender is self._shapes_combobox:
                folder = self.context.shaders_path if self.context else None
                previous_value = self.context.shapes_series if self.context else -1
            elif sender is self._texture_combobox:
                folder = self.context.texture_path if self.context else None
                previous_value = self.context.texture_series if self.context else -1
            elif sender is self._utilities_combobox:
                folder = self.context.utilities_path if self.context else None
                previous_value = self.context.utilities_series if self.context else -1

            sender.setCurrentText(f"{previous_value:03d}")

            if folder and previous_value != -1:
                dialog = CreateSeriesDialog(folder.parent, previous_value)
                dialog.exec_()
                self.update_series(folder.parent.name, self.context)
                sender.setCurrentText(f"{dialog.value:03d}")

        self.context = self.update_context()

    def _open_shapes_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.shapes_path))

    def _open_assets_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.assets_path))

    def _open_rigs_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.rigs_path))

    def _open_shaders_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.shaders_path))

    def _open_texture_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.texture_path))

    def _open_utilities_series_folder(self):
    # type: () -> None
        try:
            context = self.update_context()
        except ValueError:
            pass
        else:
            if context:
                os.startfile(str(context.utilities_path))

        
