from abc import ABC, abstractclassmethod

class TemplateModule(ABC):

    @abstractclassmethod
    def place_templates(self):
        pass

    @abstractclassmethod
    def build_template_controllers(self):
        pass

    @abstractclassmethod
    def setup(self):
        pass

class RigModule(ABC):

    @abstractclassmethod
    def place_joints(self):
        pass

    @abstractclassmethod
    def build_rig_controllers(self):
        pass

    @abstractclassmethod
    def setup(self):
        pass
    