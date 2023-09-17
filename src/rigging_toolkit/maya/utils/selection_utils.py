from maya import cmds
from typing import List

def reset_attributes_to_default(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            current_value = cmds.getAttr("{}.{}".format(obj, attr))
            default_value = cmds.attributeQuery(attr, node=obj, listDefault=True)[0]

            if current_value != default_value:
                cmds.setAttr("{}.{}".format(obj, attr), default_value)

def unlock_unhide_keyable_attrs(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            cmds.setAttr("{}.{}".format(obj, attr), lock=False, keyable=True)

def lock_keyable_attrs(selection):
    # type: (List) -> None
    for obj in selection:
    
        keyable_attributes = cmds.listAttr(obj, keyable=True)

        for attr in keyable_attributes:
            cmds.setAttr("{}.{}".format(obj, attr), lock=True)

def delete_keyframes_from_selection(selection):
    # type: (List) -> None
    cmds.cutKey(selection, s=True)

def select_hiearchy(selection):
    # type: (List) -> None
    cmds.select(selection, hi=True)