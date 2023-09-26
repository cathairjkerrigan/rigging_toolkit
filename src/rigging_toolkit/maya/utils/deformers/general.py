from maya import cmds
from typing import List

def deformers_by_type(mesh, deformer_type):
    # type: (str, str) -> List[str]
    """List all the deformers of a given type attached to the mesh."""
    deformers = [
        d for d in cmds.listHistory(mesh) or [] if cmds.nodeType(d) == deformer_type
    ]
    return deformers