from typing import Optional
from rigging_toolkit.core.context import Context
from rigging_toolkit.ui.widgets import TabWidget
from PySide2 import QtWidgets
from rigging_toolkit.maya.shaders import export_shaders, setup_shaders
from rigging_toolkit.core.filesystem import has_folders, find_latest
from maya import cmds

class TestTab(TabWidget):
    TAB_NAME = "Testing Tab"

    def __init__(self, parent=None, context=None):
        super(TabWidget, self).__init__(parent=parent)
        self.context = context
        self.child_dialogs = []

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setStretch(0, 0)
        self.setLayout(self._layout)

        self.test_button = QtWidgets.QPushButton("Test Button")

        self.test_button_2 = QtWidgets.QPushButton("Test Button 2")

        self._layout.addWidget(self.test_button)
        self._layout.addWidget(self.test_button_2)

        self.test_button.clicked.connect(self.test_func)
        self.test_button_2.clicked.connect(self.test_func_2)

    def _on_context_changed(self, context: Context | None) -> None:
        self.context = context
        self.child_dialogs = [c for c in self.child_dialogs if c != None]
        for c in self.child_dialogs:
            c._on_context_changed(context)

    def test_func(self):

        context = self.context

        print(context.character_name)
        print(context.character_path)
        print(context.animation_path)
        print(context.assets_path)
        print(context.texture_path)

        # for asset in context.assets_path.iterdir():
        #     path = asset / "meshes"
        #     name = f"geo_{asset.name}_L1"
        #     latest, _ = find_latest(path, name, "abc")
        #     cmds.file(str(latest), i=True, uns=False)

        # setup_shaders(context)



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

        context = self.context

        file_path = context.shaders_path
        meshes = cmds.ls(sl=1)
        print(meshes)

        export_shaders(meshes, file_path)

    def test_func_3(self):
        print("button is working")
