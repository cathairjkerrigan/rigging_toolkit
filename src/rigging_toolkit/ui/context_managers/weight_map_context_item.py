from typing import TYPE_CHECKING, Optional

from rigging_toolkit.maya.utils.weightmap import WeightMap
from rigging_toolkit.ui.context_managers.context_item import ContextItem
from rigging_toolkit.core.filesystem import Path

if TYPE_CHECKING:
    from rigging_toolkit.ui.context_managers.context_manager import ContextManager

class WeightMapContextItem(ContextItem):

    def __init__(self, name, weight_map, parent, file_path=None):
        super(WeightMapContextItem, self).__init__(name, weight_map, parent)
        # type: (str, WeightMap, ContextManager, Optional[Path]) -> None
        self._file_path = Path(file_path) if file_path else None

    @property
    def name(self):
        # type: () -> str
        return self.item.name
    
    @name.setter
    def name(self, name):
        # type: (str) -> None
        self.item.name = name

    @property
    def file_path(self):
        # type: () -> Path
        return self._file_path
    
    @file_path.setter
    def file_path(self, path):
        # type: (Path) -> None
        self._file_path = Path(path)

    @property
    def version(self):
        # type: () -> int
        return self._file_path.version