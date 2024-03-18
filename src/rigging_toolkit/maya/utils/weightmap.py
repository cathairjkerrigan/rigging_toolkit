from typing import List, Optional, Union, TYPE_CHECKING

import numpy as np

from rigging_toolkit.maya.utils.delta import Delta

import json

if TYPE_CHECKING:
    from rigging_toolkit.core.filesystem import Path


class WeightMap(object):
    decimals = 5  # type: int

    def __init__(self, name, values, mirror_values=None):
        # type: (str, List[float], Optional[List[float]]) -> None
        self._name = name
        self.indices = list(range(len(values)))
        self.values = values
        self.vertex_count = len(values)
        self.weights = {idx: val for idx, val in zip(self.indices, self.values)}
        self._mirror_values = mirror_values

    def get_weights(self):
        # type: () -> List
        return self.values

    def inverse(self):
        # type: () -> WeightMap
        inverted_values = 1.0 - np.array(self.values)
        return WeightMap(name=f"{self.name}_inverse", values=inverted_values)

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

    def __eq__(self, other):
        # type: (object) -> bool
        # compare vertex count and values of weight maps to determine if they are equal
        # name is ignored as we want to check if the values are equal, not the instance
        if not isinstance(other, WeightMap):
            return False
        if not self.vertex_count == other.vertex_count:
            return False
        # we use np.allclose here to deal with floating point percision inaccuracies
        # TODO add more accurate tolerance based on Maya's percision level
        if not np.allclose(self.values, other.values):
            return False
        return True

    def __ne__(self, other):
        # type: (object) -> bool
        return not self.__eq__(other)
    
    def data(self):
        # type: () -> dict
        return {"name": self.name, "values": self.values}
    
    def to_file(self, path):
        # type: (Union[Path, str]) -> None
        with open(str(path), "w") as f:
            json.dump(self.data(), f)

    @staticmethod
    def load(data):
        # type: (dict) -> WeightMap
        name = data["name"]
        values = data["values"]
        return WeightMap(name, values)

    @staticmethod
    def load_default(name, vertex_count):
        # type: (str, int) -> WeightMap
        '''
        Load a default weight map with all values set to 1.0
        '''
        values = np.ones(vertex_count)
        return WeightMap(name, values)
    
    @staticmethod
    def from_file(path):
        # type: (Union[Path, str]) -> WeightMap
        with open(str(path), "r") as f:
            data = json.load(f)

        return WeightMap.load(data)

    @staticmethod
    def normalize(weight_maps):
        # type: (List[WeightMap]) -> List[WeightMap]
        """
        Normalize a list of weight maps so that the sum of the weights for each vertex is 1.0.
        The weightmaps need to be compatible, meaning they need to have the same number of vertices.

        args:
            weight_maps(List[WeightMap]) -> List of WeightMap objects

        return:
            normalized_weight_maps(List[WeightMap]) -> List of normalized WeightMap objects
        """
        maps_compatible = all(
            x.vertex_count == weight_maps[0].vertex_count for x in weight_maps
        )
        if not maps_compatible:
            raise ValueError(
                f"Maps {[x.name for x in weight_maps]} are not compatible."
            )

        normalized_weight_maps = []

        # nr_of_vertices X nr_of_weight_maps
        weights_per_vertex = np.zeros((weight_maps[0].vertex_count, len(weight_maps)))

        for idx, weight_map in enumerate(weight_maps):
            for vtx, weight in weight_map.weights.items():
                weights_per_vertex[vtx, idx] = weight

        summed_weights_per_vertex = np.sum(weights_per_vertex, axis=1)
        indices_to_normalize = summed_weights_per_vertex[
            np.logical_and(
                summed_weights_per_vertex != 1, summed_weights_per_vertex != 0
            )
        ].nonzero()[0]
        if indices_to_normalize.size == 0:
            return weight_maps
        normalize_factor = 1.0 / summed_weights_per_vertex[indices_to_normalize]
        weights_per_vertex[indices_to_normalize] = np.multiply(
            normalize_factor[:, np.newaxis], weights_per_vertex[indices_to_normalize]
        )
        for idx, weight_map in enumerate(weight_maps):
            name = f"{weight_map.name}_normalized"
            values = weights_per_vertex[:, idx].flatten().tolist()
            normalized_weight_maps.append(WeightMap(name, values))

        return normalized_weight_maps
    
    @staticmethod
    def combine(weight_maps):
        # type: (List[WeightMap]) -> WeightMap
        '''
        Combine WeightMaps to generate a new WeightMap
        args:
            weight_maps(List[WeightMap]) -> List of WeightMap objects
        return:
            WeightMap
        '''
        vertex_count = weight_maps[0].vertex_count
        return sum(weight_maps, WeightMap("", values=np.zeros(vertex_count)))
    
    @staticmethod
    def difference(weight_maps):
        # type: (List[WeightMap]) -> WeightMap
        '''
        Subtract WeightMaps from first WeightMap in the list to generate a new WeightMap
        args:
            weight_maps(List[WeightMap]) -> List of WeightMap objects
        return:
            WeightMap
        '''
        vertex_count = weight_maps[0].vertex_count
        combined_weightmap = sum(weight_maps[1:], WeightMap("", values=np.zeros(vertex_count)))
        return weight_maps[0] - combined_weightmap
    
    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, name):
        self._name = name
    
    @property
    def mirror(self):
        # type: () -> WeightMap
        return WeightMap(name=f"{self.name}_mirror_map", values=self._mirror_values, mirror_values=self.values)
    
    @mirror.setter
    def mirror(self, values):
        # type: (List[float]) -> None
        if not len(values) == self.vertex_count:
            raise ValueError(f"Mirror values count does not match WeightMap values count. Expected {self.vertex_count}, got {len(values)}")
        if not np.allclose(values, self.values):
            self._mirror_values = values
        else:
            raise ValueError("Mirror values match current WeightMap, please provide valid mirror values.")

    @staticmethod
    def from_file(path):
        # type: (Union[Path, str]) -> WeightMap
        with open(str(path), "r") as f:
            data = json.load(f)

        return WeightMap.load(data)

