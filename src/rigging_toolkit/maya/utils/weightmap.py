from typing import List, Optional

import numpy as np

from rigging_toolkit.maya.utils.delta import Delta


class WeightMap(object):
    decimals = 5  # type: int

    def __init__(self, name, values):
        # type: (str, List[float]) -> None
        self.name = name
        self.indices = list(range(len(values)))
        self.values = values
        self.vertex_count = len(values)
        self.weights = {idx: val for idx, val in zip(self.indices, self.values)}

    def get_weights(self):
        # type: () -> List
        return self.values

    def __add__(self, other):
        # type: (WeightMap) -> Optional[WeightMap]
        # compare the indices of the delta objects
        if self.vertex_count != other.vertex_count:
            return None
        svalues, ovalues = np.array(self.values, dtype=np.float32), np.array(
            other.values, dtype=np.float32
        )
        new_values = svalues + ovalues
        new_values[new_values > 1.0] = 1.0
        new_values[new_values < 0.0] = 0.0
        return WeightMap(f"{self.name}+{other.name}", new_values.tolist())

    def __sub__(self, other):
        # type: (WeightMap) -> Optional[WeightMap]
        # compare the indices of the delta objects
        if self.vertex_count != other.vertex_count:
            return None
        svalues, ovalues = np.array(self.values, dtype=np.float32), np.array(
            other.values, dtype=np.float32
        )
        new_values = np.round(svalues - ovalues, decimals=WeightMap.decimals)
        new_values[new_values > 1.0] = 1.0
        new_values[new_values < 0.0] = 0.0
        return WeightMap(f"{self.name}-{other.name}", new_values.tolist())

    def __mul__(self, other):
        # type: (Delta) -> Delta
        # compare the indices of the delta objects
        # TODO add a check for compatibility
        svalues, ovalues = np.array(self.values, dtype=np.float32)[
            other.indices
        ], np.array(other.deltas, dtype=np.float32)
        new_values = svalues[:, np.newaxis] * ovalues
        return Delta(
            f"{other.name}_{self.name}", deltas=new_values, indices=other.indices
        )

    def data(self):
        # type: () -> dict
        return {"name": self.name, "values": self.values}

    @staticmethod
    def load(data):
        # type: (dict) -> WeightMap
        name = data["name"]
        values = data["values"]
        return WeightMap(name, values)
