from PySide2 import QtWidgets

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from rigging_toolkit.maya.utils import toggle_template_display_for_all_meshes
from rigging_toolkit.core import Context
from rigging_toolkit.core.filesystem import has_folders, find_latest
from pathlib import Path
from maya import cmds
from rigging_toolkit.maya.shaders.build_shaders import PBRShader, setup_textures
from rigging_toolkit.maya.assets.asset_manager import export_all_character_assets
from rigging_toolkit.maya.rigging import load_from_json, save_to_json
import pprint

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

        self.test_button_2 = QtWidgets.QPushButton("Test Button 2")

        self._layout.addWidget(self.test_button)
        self._layout.addWidget(self.test_button_2)

        self.test_button.clicked.connect(self.test_func)
        self.test_button_2.clicked.connect(self.test_func_2)

        self.context = Context.new(
            project_path=Path(r"F:\university_work\major_project\characters"),
            character_name="kate",
            create_context=True
        )

    def test_func(self):

        print(self.context.character_name)
        print(self.context.character_path)
        print(self.context.animation_path)
        print(self.context.assets_path)
        print(self.context.texture_path)

        for asset in self.context.assets_path.iterdir():
            path = asset / "meshes"
            name = f"geo_{asset.name}_L1"
            latest, _ = find_latest(path, name, "abc")
            cmds.file(str(latest), i=True, uns=False)

        setup_textures(self.context)

    def test_func_2(self):
        # ctrls = cmds.ls(sl=1)

        path = r"F:\university_work\controller_test.json"

        # save_to_json(ctrls, path)

        # cmds.file(new=True, f=True)

        controllers = load_from_json(path)

        # controller[0].apply(create_missing=True)
        for controller in controllers:
            controller.apply(create_missing=True)

        # pprint.pprint(ctrls)
        # cmds.file(new=True, f=True)
        # ctrls.apply(create_missing=True)