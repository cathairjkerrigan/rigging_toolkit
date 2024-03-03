from maya import cmds
import maya.api.OpenMaya as om2
from dataclasses import dataclass, field
from typing import List
import logging

logger = logging.getLogger(__name__)

@dataclass(frozen=True,order=True)
class JointPatternItem:
    vertex_id: int = field(default=-1)
    world_pos: om2.MPoint = field(default=None)

@dataclass(frozen=True,order=True)
class JointPattern:
    mesh: str = field(default="")
    vertices: List[str] = field(default_factory=[])
    follicles = List[str] = field(default_factory=[])
    items = List[JointPatternItem]