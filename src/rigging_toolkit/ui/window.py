from PySide2 import QtWidgets, QtGui

from maya.app.general.mayaMixin import MayaQWidgetDockableMixin

from rigging_toolkit.maya.utils import toggle_template_display_for_all_meshes
from rigging_toolkit.core import Context
from rigging_toolkit.core.filesystem import has_folders, find_latest
from pathlib import Path
from rigging_toolkit.maya.shaders import PBRShader, setup_pbr_textures
from rigging_toolkit.maya.assets.asset_manager import export_all_character_assets
import pprint
from rigging_toolkit.ui.context_ui import ContextUI
from rigging_toolkit.maya.shaders import export_shaders, setup_shaders
from rigging_toolkit.ui.widgets import TabWidget
from rigging_toolkit.ui.tabs.assets import AssetsTab
from maya import cmds

from rigging_toolkit.ui.tabs.test_tab import TestTab

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

        self.initial_directory = cmds.internalVar(userPrefDir=True)

        self.ignore_list = ["_ignore"]

        self._layout = QtWidgets.QVBoxLayout()
        
        self.setLayout(self._layout)

        self.context_ui = ContextUI()
        self._layout.addWidget(self.context_ui)
        self._tab_widget = QtWidgets.QTabWidget()
        self._layout.addWidget(self._tab_widget)

        self.test_tab = TestTab(context=self.context())
        self.add_tab(self._tab_widget, self.test_tab)

        self.assets_tab = AssetsTab(context=self.context())
        self.add_tab(self._tab_widget, self.assets_tab)

    
        self._layout.addStretch() 

        self._context = self.context()

    def context(self):#
        context = self.context_ui.update_context()
        return context
    
    def dockCloseEventTriggered(self):
        # type: () -> None
        self.context_ui.save_settings()

    def add_tab(self, tab_widget, child_widget):
        # type: (QtWidgets.QTabWidget, TabWidget) -> None
        self.context_ui.context_changed.connect(child_widget._on_context_changed)
        tab_widget.addTab(child_widget, child_widget.TAB_NAME)



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