from maya import cmds
import maya.api.OpenMaya as om2

from dataclasses import dataclass, field, asdict, fields
from typing import Optional, NamedTuple, List, Text
from six import iteritems


from pathlib import Path
import json
import logging

from enum import IntEnum

logger = logging.getLogger(__name__)

class CurveType(IntEnum):
    open = 1
    closed = 2
    periodic = 3

Color = NamedTuple("Color", [("r", float), ("g", float), ("b", float)])

CV = NamedTuple("CV", [("x", float), ("y", float), ("z", float), ("w", float)])

def default_color():
    # type: () -> Color
    return Color(0,0,0)

def _get_maya_obj(node_name):
    # type: (str) -> om2.MObject
    sel = om2.MSelectionList()
    sel.add(node_name)
    return sel.getDependNode(0)

@dataclass()
class Curve:
    degree: int = field(default=1)
    form: CurveType = field(default=CurveType.open)
    overrideRGBColors: bool = field(default=False)
    overrideEnabled: bool = field(default=False)
    useOutlinerColor: bool = field(default=False)
    outlinerColor: Color = field(default_factory=default_color)
    overrideColorRGB: Color = field(default_factory=default_color)
    cvs: List[CV] = field(default_factory=list)
    knots: List[float] = field(default_factory=list)

    @classmethod
    def from_existing(cls, maya_obj):
        # type: (om2.MObject) -> Curve

        if not maya_obj.hasFn(om2.MFn.kNurbsCurve):
            raise TypeError(f"mobject should have the 'kNurbsCurve function set")
        
        dag_node_fn = om2.MFnDagNode(maya_obj)

        name = dag_node_fn.name()

        curve_fn = om2.MFnNurbsCurve(maya_obj)

        knots = [f for f in curve_fn.knots()]
        cvs = [CV(*mp) for mp in curve_fn.cvPositions()]
        form = CurveType(curve_fn.form)
        degree = curve_fn.degree
        overrideRGBColors = cmds.getAttr(f"{name}.overrideRGBColors")
        overrideColorRGB = Color(*cmds.getAttr(f"{name}.overrideColorRGB")[0])
        overrideEnabled = cmds.getAttr("{}.overrideEnabled".format(name))
        useOutlinerColor = cmds.getAttr("{}.useOutlinerColor".format(name))
        outlinerColor = Color(*cmds.getAttr("{}.outlinerColor".format(name))[0])

        return cls(
            degree=degree,
            form=form,
            overrideRGBColors=overrideRGBColors,
            overrideEnabled=overrideEnabled,
            useOutlinerColor=useOutlinerColor,
            outlinerColor=outlinerColor,
            overrideColorRGB=overrideColorRGB,
            cvs=cvs,
            knots=knots,
        )
    
    def apply(self, parent, index):
        # type: (om2.MObject, int) -> None

        curve_fn = om2.MFnNurbsCurve()
        maya_obj = curve_fn.create(
            self.cvs, self.knots, self.degree, int(self.form), False, False, parent
        )

        parent_transform_fn = om2.MFnDagNode(parent)
        curve_transform_fn = om2.MFnDagNode(maya_obj)

        parent_name = parent_transform_fn.name()
        curve_name = f"{parent_name}Shape{index+1}"
        curve_transform_fn.setName(curve_name)

        cmds.setAttr(f"{curve_name}.overrideRGBColors", self.overrideRGBColors)
        cmds.setAttr(f"{curve_name}.overrideColorRGB", *self.overrideColorRGB)
        cmds.setAttr(f"{curve_name}.overrideEnabled", self.overrideEnabled)
        cmds.setAttr(f"{curve_name}.useOutlinerColor", self.useOutlinerColor)
        cmds.setAttr(f"{curve_name}.outlinerColor", *self.outlinerColor)

        logger.info(f"Applied curves on control: {parent_name}")



@dataclass()
class Control:
    name: Text = field(default="")
    curves: List[Curve] = field(default_factory=list)

    @classmethod
    def from_existing(cls, control):
        # type: (Text) -> Control
        maya_obj = _get_maya_obj(control)
        transform_fn = om2.MFnTransform(maya_obj)
        dag_node_fn = om2.MFnDagNode(maya_obj)

        curves = []
        for i in range(transform_fn.childCount()):
            child = transform_fn.child(i)
            if not child.hasFn(om2.MFn.kNurbsCurve):
                continue
            curve = Curve.from_existing(child)
            curves.append(curve)

        return cls(dag_node_fn.name(), curves=curves)

    def apply(self, create_missing=False):
        # type: (bool) -> bool
        try:
            if not cmds.objExists(self.name):
                if create_missing:
                    cmds.createNode("transform", name=self.name)
                    logger.debug(f"Creating control: {self.name}")
                else:
                    logger.info(f"Ignored curves for non existing control: {self.name}")
                    return False

            maya_obj = _get_maya_obj(self.name)

            self.delete_shapes()
            for i, curve in enumerate(self.curves):
                curve.apply(maya_obj, i)

            return True
        except BaseException:
            logger.exception(f"Failed to instantiate control {self.name}")
            return False

    def delete_shapes(self):
        # type: () -> None
        if cmds.objExists(self.name):
            shapes = cmds.listRelatives(self.name, shapes=True, fullPath=True)
            if shapes:
                logger.debug(f"Deleting existing curves on control: {self.name}")
                for shape in shapes:
                    if cmds.nodeType(shape) == "nurbsCurve":
                        cmds.delete(shape)


# def dataclass_from_dict(klass, dikt):
#     try:
#         fieldtypes = klass.__annotations__
#         return klass(**{f: dataclass_from_dict(fieldtypes[f], dikt[f]) for f in dikt})
#     except AttributeError:
#         if isinstance(dikt, (tuple, list)):
#             return [dataclass_from_dict(klass.__args__[0], f) for f in dikt]
#         return dikt

# def extract_controls(controls):
#     control_list = [Control.from_existing(control) for control in controls]

#     return control_list

# def extract_control(control):
#     # type: (str) -> Control

#     controller = Control.from_existing(control)

#     return controller

# def export_control(control):

#     controller = extract_control(control)

#     data = asdict(controller)

#     print(data)

# Serialization
def serialize_control(control):
    return asdict(control)

# Deserialization
def deserialize_control(control_data):
    control_data["curves"] = [Curve(**curve_data) for curve_data in control_data["curves"]]
    return Control(**control_data)

# Saving to a JSON file
def save_to_json(controls, filename):
    control_list = [Control.from_existing(control) for control in controls]
    with open(filename, 'w') as file:
        json.dump([serialize_control(control) for control in control_list], file, indent=4)

# Loading from a JSON file
def load_from_json(filename):
    with open(filename, 'r') as file:
        controls_data = json.load(file)
    return [deserialize_control(control_data) for control_data in controls_data]



