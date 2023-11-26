from PySide2 import QtWidgets, QtGui

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from rigging_toolkit.maya.utils import toggle_template_display_for_all_meshes
from rigging_toolkit.core import Context
from rigging_toolkit.core.filesystem import has_folders, find_latest
from pathlib import Path
from maya import cmds
from rigging_toolkit.maya.shaders import PBRShader, setup_pbr_textures
from rigging_toolkit.maya.assets.asset_manager import export_all_character_assets
from rigging_toolkit.maya.rigging import load_from_json, save_to_json
import pprint
from rigging_toolkit.ui.context_ui import ContextUI
from rigging_toolkit.maya.shaders import export_shaders, setup_shaders

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

        self._context = None

        self.initial_directory = cmds.internalVar(userPrefDir=True)

        self.ignore_list = ["_ignore"]

        self._layout = QtWidgets.QVBoxLayout()
        
        self.setLayout(self._layout)

        self.test_button = QtWidgets.QPushButton("Test Button")

        self.test_button_2 = QtWidgets.QPushButton("Test Button 2")

        self.context_ui = ContextUI()
        self._layout.addWidget(self.context_ui)

        self._layout.addWidget(self.test_button)
        self._layout.addWidget(self.test_button_2)

        self.test_button.clicked.connect(self.test_func)
        self.test_button_2.clicked.connect(self.test_func_2)

        # self.dir_pushbutton.clicked.connect(self.open_dir)

        # self.dir_lineedit.textChanged.connect(self._populate_character_combobox)

        # self.char_combobox.currentIndexChanged.connect(self.update_context)

        self._layout.addStretch() 

    def context(self):
        return self.context_ui.update_context()
    
    def dockCloseEventTriggered(self):
        # type: () -> None
        self.context_ui.save_settings()

    def test_func(self):

        context = self.context()

        print(context.character_name)
        print(context.character_path)
        print(context.animation_path)
        print(context.assets_path)
        print(context.texture_path)

        for asset in context.assets_path.iterdir():
            path = asset / "meshes"
            name = f"geo_{asset.name}_L1"
            latest, _ = find_latest(path, name, "abc")
            cmds.file(str(latest), i=True, uns=False)

        setup_shaders(context)



    def test_func_2(self):
        # # ctrls = cmds.ls(sl=1)

        # path = r"F:\university_work\controller_test.json"

        # # save_to_json(ctrls, path)

        # # cmds.file(new=True, f=True)

        # controllers = load_from_json(path)

        # # controller[0].apply(create_missing=True)
        # for controller in controllers:
        #     controller.apply(create_missing=True)

        # # pprint.pprint(ctrls)
        # # cmds.file(new=True, f=True)
        # # ctrls.apply(create_missing=True)

        context = self.context()

        file_path = context.shaders_path
        meshes = cmds.ls(sl=1)
        print(meshes)

        export_shaders(meshes, file_path)

    def test_func_3(self):
        print("button is working")