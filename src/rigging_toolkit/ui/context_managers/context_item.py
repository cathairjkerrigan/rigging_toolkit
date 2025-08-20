from typing import Any, TYPE_CHECKING
from rigging_toolkit.ui.context_managers.context_manager import ContextManager

class ContextItem(object):

    def __init__(self, name, item, parent):
        # type: (str, Any, ContextManager) -> None
        self._name = name
        self._item = item
        self._parent = parent

    @property
    def name(self):
        return self._name
    
    @name.setter
    def name(self, new_name):
        self._name = new_name

    @property
    def item(self):
        return self._item
    
    @item.setter
    def item(self, new_item):
        self._item = new_item

    @property
    def parent(self):
        return self._parent
    
    @parent.setter
    def parent(self, new_parent):
        if not isinstance(new_parent, ContextManager):
            raise ValueError(f"Parent {new_parent} is not an instance of ContextManager")
        
        self._parent.remove_item(self._name)

        self._parent = new_parent

        self._parent.add_item(self.name, self)