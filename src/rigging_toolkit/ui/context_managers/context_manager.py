from typing import Any
from rigging_toolkit.ui.context_managers.context_item import ContextItem

class ContextManager(object):

    def __init__(self):
        
        self._context_items = {}

    def add_item(self, name, item):
        # type: (str, Any) -> None
        context_item = ContextItem(item)

        self._context_items[name] = context_item

    def get_item(self, name):
        # type: (str) -> ContextItem
        return self._context_items.get(name)
    
    def remove_item(self, name):
        # type: (str) -> None
        self._context_items.pop(name)

    def clear_items(self):
        # type: () -> None
        self._context_items.clear()

    @property
    def items(self):
        return list(self._context_items.keys())