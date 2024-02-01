from typing import List, Optional, Generator, Tuple

import numpy as np

from maya import cmds
import logging
logger = logging.getLogger(__name__)
from contextlib import contextmanager

class Delta(object):
    def __init__(self, name, indices, deltas):
        # type: (str, List, List) -> None
        self.name = name
        self.indices = indices
        self.deltas = np.array(deltas)

    def __sub__(self, other):
        # type: (Delta) -> Optional[Delta]
        # compare the indices of the delta objects
        all_indices = list(set.union(set(self.indices), set(other.indices)))
        if len(all_indices) == 0:
            return None

        values1 = np.zeros(shape=(len(all_indices), 3))
        indices1 = [all_indices.index(idx) for idx in self.indices]
        values1[indices1] = self.deltas

        values2 = np.zeros(shape=(len(all_indices), 3))
        indices2 = [all_indices.index(idx) for idx in other.indices]
        values2[indices2] = other.deltas

        nvalues = values1 - values2
        return Delta(f"{self.name}-{other.name}", all_indices, nvalues)

    def __add__(self, other):
        # type: (Delta) -> Optional[Delta]
        # compare the indices of the delta objects
        all_indices = list(set.union(set(self.indices), set(other.indices)))
        if len(all_indices) == 0:
            return None

        values1 = np.zeros(shape=(len(all_indices), 3))
        indices1 = [all_indices.index(idx) for idx in self.indices]
        values1[indices1] = self.deltas

        values2 = np.zeros(shape=(len(all_indices), 3))
        indices2 = [all_indices.index(idx) for idx in other.indices]
        values2[indices2] = other.deltas

        nvalues = values1 + values2
        return Delta(f"{self.name}+{other.name}", all_indices, nvalues)

    def __eq__(self, other):
        # type: (object) -> bool
        if not isinstance(other, Delta):
            return False
        if not self.indices == other.indices:
            return False
        return np.all(self.deltas == other.deltas)

    def __ne__(self, other):
        # type: (object) -> bool
        return not self.__eq__(other)

    def data(self):
        # type: () -> dict
        return {
            "name": self.name,
            "indices": self.indices,
            "deltas": self.deltas.tolist(),
        }

    @staticmethod
    def load(data):
        # type: (dict) -> Delta
        return Delta(data["name"], data["indices"], data["deltas"])
    
class ExtractCorrectiveDelta(object):

    PLUGIN_NAME = "invertShape.mll"

    @classmethod
    def ensure_availability(cls):
        # type: () -> bool
        if cmds.pluginInfo(cls.PLUGIN_NAME, q=True, loaded=True):
            return True

        try:
            if cmds.loadPlugin(cls.PLUGIN_NAME):
                return True
        except BaseException as e:
            logger.error("Error loading ExtractDelta Plugin: {0}" + str(e))
        return False

    @classmethod
    def calculate(cls, to_correct, corrective):
        # type: (str, str) -> str
        cls.ensure_availability()

        with cls.disconnect_blendshape_targets(to_correct):
            delta_mesh = cmds.invertShape(to_correct, corrective)  # type: str
            delta_mesh = cmds.rename(delta_mesh, corrective + "_delta")
            return delta_mesh

    @staticmethod
    @contextmanager
    def disconnect_blendshape_targets(mesh):
        # type: (str) -> Generator

        connections = []  # type: List[Tuple]

        blendshape_nodes = [
            d for d in cmds.listHistory(mesh) or [] if cmds.nodeType(d) == "blendShape"
        ]
        for blendshape_node in blendshape_nodes:

            target_meshes = (
                cmds.blendShape(blendshape_node, query=True, target=True) or []
            )

            for target_mesh in target_meshes:
                source_attr = "{}.worldMesh[0]".format(target_mesh)
                target_attr = cmds.listConnections(
                    source_attr,
                    source=True,
                    destination=True,
                    plugs=True,
                )[0]
                connections.append((source_attr, target_attr))
                cmds.disconnectAttr(source_attr, target_attr)

        yield

        for source_attr, target_attr in connections:
            cmds.connectAttr(source_attr, target_attr)