from maya import cmds
from typing import Optional

AXIS = ["x", "y", "z"]

def set_controller_color(shape, color):
    # type: (str, int) -> None
    cmds.setAttr(f"{shape}.overrideEnabled", 1)
    cmds.setAttr(f"{shape}.overrideColor", color)

def set_scale(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.s{i}", value)

def set_rotation(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.r{i}", value)

def set_translation(object, value):
    # type: (str, int) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.t{i}", value)

def lock_translate(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.t{i}", l=lock)

def lock_rotation(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.r{i}", l=lock)

def lock_scale(object, lock=True):
    # type: (str, Optional[bool]) -> None
    for i in AXIS:
        cmds.setAttr(f"{object}.s{i}", l=lock)

def toggle_visibility(object):
    # type: (str) -> None
    visibility_state = cmds.getAttr(f"{object}.v")
    if visibility_state == 0:
        cmds.setAttr(f"{object}.v", 1)
    else:
        cmds.setAttr(f"{object}.v", 0)

def toggle_template(object):
    # type: (str) -> None
    template_state = cmds.getAttr(f"{object}.template")
    if template_state == 0:
        cmds.setAttr(f"{object}.template", 1)
    else:
        cmds.setAttr(f"{object}.template", 0)

def joint_label(transform, name, side):

    cmds.setAttr(f"{transform}.side", side)
    cmds.setAttr(f"{transform}.type", 18)
    cmds.setAttr(f"{transform}.otherType", name, typ='string')
