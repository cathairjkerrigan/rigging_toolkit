from typing import Optional, List
from rigging_toolkit.maya.utils import list_shapes
import logging
from rigging_toolkit.core.filesystem import Path
from rigging_toolkit.maya.utils.deformers.blendshape import (
    apply_weightmap_to_target,
    combine_weight_maps,
    get_weights_from_blendshape,
    get_weights_from_blendshape_target,
    inverse_target_weightmap,
    list_shapes,
    mirror_weight_map_by_pos,
    set_delta_weightmap_to_target,
    subtract_weight_maps,
    mirror_weight_map_by_topology_selection
)
from rigging_toolkit.maya.utils.weightmap import WeightMap
from rigging_toolkit.ui.context_managers.context_manager import ContextManager

logger = logging.getLogger(__name__)

class WeightMapContextManager(ContextManager):

    def __init__(self, blendshape):
        super(WeightMapContextManager, self).__init__()
        self._blendshape = blendshape
        self._load()

    @property
    def blendshape(self):
        # type: () -> List[str]
        return self._blendshape
    
    @blendshape.setter
    def blendshape(self, blendshape):
        # type: (str) -> None
        self._blendshape = blendshape
    
    def _load(self):
        # type: () -> None
        weight_maps = get_weights_from_blendshape(self.blendshape)
        for wm in weight_maps:
            self.add_item(wm.name, wm)