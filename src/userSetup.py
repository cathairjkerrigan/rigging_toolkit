import maya.cmds as cmds
from textwrap import dedent

# Schedule startup to be initialised
cmds.evalDeferred(
    dedent(
        """
        from core.startup import build_enviroment
        build_enviroment()
        """
    ),
    lp=True,
)