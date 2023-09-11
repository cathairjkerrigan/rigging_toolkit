import maya
import rigging_toolkit
from textwrap import dedent

# Schedule startup to be initialised
maya.cmds.evalDeferred(
    dedent(
        """
        from rigging_toolkit.core.startup import startup
        startup()
        """
    ),
    lp=True,
)