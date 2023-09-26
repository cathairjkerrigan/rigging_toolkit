from maya import cmds
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def list_verticies(mesh):
    # type: (str) -> List
    return cmds.ls("{}.vtx[*]".format(mesh), fl=True)

def get_parent(mesh):
    # type: (str) -> Optional[str]
    parent = cmds.listRelatives(mesh, p=True)
    if parent:
        return parent[0]
    return None

def get_shapes(mesh):
    # type: (str) -> Optional[List]
    shapes = cmds.listRelatives(mesh, shapes=True)
    if shapes: 
        return shapes
    return None
