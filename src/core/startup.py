from logging import getLogger
from typing import Any
from maya import cmds, mel
from textwrap import dedent

logger = getLogger(__name__)

from core.module_handler import reload_module

VERSION = "v.1.0.0"

def build_enviroment():
    # type: () -> None
    mel.eval('source "artAttrCreateMenuItems.mel";')
    build_menu()

def reload(*args):
    # type: (Any) -> None
    reload_module("rigging_toolkit", True)
    cmds.evalDeferred(
        dedent(
            """
            from core.startup import build_menu
            build_menu()
            """
        ),
        lp=True,
    )

def run_tests(*args):
    # type: (Any) -> None
    logger.warning("TO DO: Add functionality to run tests inside of Maya")

def check_for_updates(*args):
    # type: (Any) -> None
    logger.warning("TO DO: Add functionality to check for updates and install them inside of Maya")


def build_menu():
    # type: () -> None

    logger.info("Building Rigging Toolkit Menu")

    MENU_NAME = "rigging_toolkit_menu"
    MENU_ITEMS = [
        {
            "name": "open_toolkit",
            "command": "from rigging_toolkit.ui import RiggingToolboxWindow;RiggingToolboxWindow.open()",
            "label": "Open Toolkit",
        },
        {
            "name": "reload_toolkit",
            "command": reload,
            "label": "Reload Toolkit",
        },
        {
            "name": "seperator_01",
            "divider": True,
        },
        {
            "name": "run_tests",
            "command": run_tests,
            "label": "Run Tests",
        },
        {
            "name": "seperator_02",
            "divider": True,
        },
        {
            "name": "update_checker",
            "command": check_for_updates,
            "label": "Check For Updates",
        },
        {
            "name": "version_info",
            "command": "pass",
            "label": "Version: {}".format(VERSION)
        }
    ]

    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.menu(MENU_NAME, edit=True, deleteAllItems=True)
    else:
        cmds.menu(MENU_NAME, label="Rigging Toolkit", parent="MayaWindow", tearOff=False)

    for data in MENU_ITEMS:
        name = data.pop("name")
        cmds.menuItem(name, parent=MENU_NAME, **data)