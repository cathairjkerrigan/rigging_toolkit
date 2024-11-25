
# coding=future_fstrings
from __future__ import absolute_import, division, print_function

from typing import TYPE_CHECKING, List, Optional, Union

import json

import numpy as np

if TYPE_CHECKING:
    from rigging_toolkit.core.filesystem import Path

class SkinWeights(object):

    def __init__(
            self,
            name, # type: str
            weights, # type: dict
            max_influences=8, # type: Optional[int]
    ):
        '''
        :param name: The name of the skin weights
        :param weights: The weights data
        :param max_influences: The maximum number of influences
        '''
        self._name = name
        self._weights = weights
        self._max_influences = max_influences

    @property
    def name(self):
        # type: () -> str
        return self._name
    
    @name.setter
    def name(self, name):
        # type: (str) -> None
        self._name = name
    
    @property
    def weights(self):
        # type: () -> dict
        return self._weights
    
    @weights.setter
    def weights(self, weights):
        # type: (dict) -> None
        self._weights = weights

    @property
    def influences(self):
        # type: () -> List[str]
        return self.weights["influences"]
    
    @property
    def num_influences(self):
        # type: () -> int
        return len(self.influences)
    
    @influences.setter
    def influences(self, influences):
        # type: (List[str]) -> None
        self.weights["influences"] = influences
        
    @property
    def max_influences(self):
        # type: () -> int
        return self._max_influences
    
    @max_influences.setter
    def max_influences(self, max_influences):
        # type: (int) -> None
        self._max_influences = max_influences
        self._check_max_influences(max_influences)

    @property
    def is_normalized(self):
        # type: () -> bool
        return all(self._weights_normalized())
    
    @property
    def num_weights(self):
        # type: () -> int
        return len(self.weights["weights"])
        
    def _check_max_influences(self, max_influences, prune=True):
        # type: (int, Optional[bool]) -> List[int]
        weights = self.weights["weights"]
        weights_influences = [len(x.keys()) for x in weights]
        above_max_influences = [i for i, num in enumerate(weights_influences) if num > max_influences]
        if above_max_influences and prune:
            self._prune_influences(max_influences, above_max_influences)
        return above_max_influences

    def _prune_influences(self, max_influences, weight_ids=None):
        # type: (int, Optional[List[int]]) -> None
        weights = self.weights["weights"]
        if not weight_ids:
            weights_influences = [len(x.keys()) for x in weights]
            above_max_influences = [i for i, num in enumerate(weights_influences) if num > max_influences]
        else:
            above_max_influences = weight_ids
        for i in above_max_influences:
            weight = weights[i]
            pruned_weights = self._prune_weights(weight, max_influences)
            weights[i] = pruned_weights
        self.weights["weights"] = weights

    def _prune_weights(self, weights, max_influences):
        # type: (dict, int) -> dict
        if len(weights.keys()) > max_influences:
            sorted_items = sorted(weights.items(), key=lambda item: item[1], reverse=True)[:max_influences]
            weights = dict(sorted_items)
        normalized_weights = self._normalize_weights(weights)
        return normalized_weights
    
    def _normalize_weights(self, weights):
        # type: (dict) -> dict
        total = sum(weights.values())
        normalized_weights = {key: value / total for key, value in weights.items()}
        return normalized_weights
    
    def prune_influences(self, max_influences=None, weight_ids=None):
        # type: (Optional[int], Optional[List[int]]) -> None
        if not max_influences:
            max_influences = self.max_influences
        self._prune_influences(self.max_influences, weight_ids=weight_ids)

    def check_max_influences(self, max_influences=None, prune=True):
        # type: (Optional[int], Optional[bool]) -> List[int]
        if not max_influences:
            max_influences = self.max_influences
        return self._check_max_influences(max_influences, prune=prune)
        
    def _weights_normalized(self):
        # type: () -> List[int]
        weights = self.weights["weights"]
        are_normalised = [
            np.isclose(np.sum(list(data.values())), 1.0)
            for data in weights["weights"]
        ]
        not_normalized = [
            i for i, normalized in enumerate(are_normalised) if not normalized
        ]
        return not_normalized
    
    def normalize(self):
        # type: () -> None
        not_normalized = self._weights_normalized()
        if not not_normalized:
            return
        weights = self.weights["weights"]
        for i in not_normalized:
            weights[i] = self._normalize_weights(weights[i])
        self.weights["weights"] = weights

    def rename_influence(self, old_name, new_name):
        # type: (str, str) -> None
        influences = self.weights["influences"]
        idx = influences.index(old_name) if old_name in influences else None
        influences[idx] = new_name
        self.weights["influences"] = influences

    def to_dict(self):
        # type: () -> dict
        return {
            "name": self.name,
            "weights": self.weights,
            "max_influences": self.max_influences
        }
    
    def to_file(self, path):
        # type: (Union[str, Path]) -> None
        with open(str(path), "w") as f:
            json.dump(self.to_dict(), f, indent=4)
    
    @classmethod
    def from_dict(cls, data):
        # type: (dict) -> SkinWeights
        return cls(data["name"], data["weights"], data["max_influences"])

    @classmethod
    def from_file(cls, path):
        # type: (Union[str, Path]) -> SkinWeights
        with open(str(path), "r") as f:
            data = json.load(f)
        return cls.from_dict(data)
