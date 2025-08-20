from maya import cmds

from rigging_toolkit.maya.rigging import TemplateModule
from dataclasses import dataclass, field, yt
from typing import List, Optional

@dataclass(frozen=True,order=True)
class LegModule:

    joints: list[str] = field(default_factory=list)
    

