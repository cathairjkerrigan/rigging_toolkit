from textwrap import dedent

from .shelf import Shelf

class ToolkitShelf(Shelf):

    def __init__(self):
        # type: () -> None
        Shelf.__init__(self, name="Toolkit_Utils")

    def build(self):
        
        self.addButton(
            label="Reset Attributes",
            tooltip="Reset all attributes from selection to their default values.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import reset_attributes_to_default
                from maya import cmds
                reset_attributes_to_default(cmds.ls(sl=1))
                """
            )
        )

        self.addButton(
            label="Delete Keyframes",
            tooltip="Delete all keyframes from selection.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import delete_keyframes_from_selection
                from maya import cmds
                delete_keyframes_from_selection(cmds.ls(sl=1))
                """
            )
        )

        self.addButton(
            label="Select Hierarchy",
            tooltip="Select hierarchy of selection.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import select_hiearchy
                from maya import cmds
                select_hiearchy(cmds.ls(sl=1))
                """
            )
        )

        self.addSeperator()

        self.addButton(
            label="Lock Keyable Attributes",
            tooltip="Lock all keyable attributes for selected objects.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import lock_keyable_attrs
                from maya import cmds
                lock_keyable_attrs(cmds.ls(sl=1))
                """
            )
        )

        self.addButton(
            label="Unlock Unhide Keyable Attributes",
            tooltip="Unlock and unhide all keyable attributes for selected objects.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import unlock_unhide_keyable_attrs
                from maya import cmds
                unlock_unhide_keyable_attrs(cmds.ls(sl=1))
                """
            )
        )

        self.addSeperator()

        self.addButton(
            label="Clean Joint Rotations",
            tooltip="Clean selected joint rotations.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import clean_joint_rotation_for_selected
                clean_joint_rotation_for_selected()
                """
            )
        )

        self.addSeperator()

        self.addButton(
            label="Delete Namespaces",
            tooltip="Delete all namespaces in the scene.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import delete_namespaces
                delete_namespaces()
                """
            )
        )

        self.addButton(
            label="Remove Unknown Nodes",
            tooltip="Delete all unknown nodes in the scene.",
            command=dedent(
                """
                from rigging_toolkit.maya.utils import delete_unknown_nodes
                delete_unknown_nodes()
                """
            )
        )

