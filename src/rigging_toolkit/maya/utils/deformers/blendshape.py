from maya import cmds
from typing import List, Optional
import re
from rigging_toolkit.maya.utils.deformers.general import deformers_by_type
from rigging_toolkit.maya.utils.delta import Delta
from rigging_toolkit.maya.utils.weightmap import WeightMap
from rigging_toolkit.core.filesystem import find_new_version
from rigging_toolkit.maya.utils.mesh_utils import get_all_meshes
from rigging_toolkit.maya.utils.delta import ExtractCorrectiveDelta
from pathlib import Path
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

def list_shapes(blendshape, exact_type=None):
    # type: (str, Optional[str]) -> List[str]
    """Get list of shapes for given blendshape node"""
    shapes = []
    for attr in cmds.ls("{}.w[*]".format(blendshape)):
        _, target = attr.split(".")
        if exact_type and exact_type not in target:
            continue
        shapes.append(target)
    return shapes

def get_target_index(blendshape, target_name):
    # type: (str, str) -> int
    """Get the target index for the given target name"""
    target_index = -1
    alias_list = cmds.aliasAttr(blendshape, query=True)
    alias_index = alias_list.index(target_name)
    alias_attr = alias_list[alias_index + 1]
    match = re.findall(r"[0-9]+", alias_attr)
    if match:
        target_index = int(match[0])
    return target_index

def add_blendshape_target(blendshape, target):
    # type: (str, str) -> str
    shapes = list_shapes(blendshape)
    mesh = cmds.blendShape(blendshape, q=True, geometry=True)[0]
    geo = cmds.listRelatives(mesh, p=True)[0]
    last_index = 0

    if len(shapes) > 0:
        last_shape = list_shapes(blendshape)[-1]
        last_index = get_target_index(blendshape, last_shape)
        new_index = last_index + 1
    else:
        new_index = last_index + 1
    cmds.blendShape(blendshape, edit=True, target=(geo, new_index, target, 1.0))
    return target

def add_blendshape_targets(blendshape, targets):
    # type: (str, List[str]) -> List[str]
    for target in targets:
        add_blendshape_target(blendshape, target)

def reset_blendshape_targets(blendshape_name):
    # type: (str) -> None
    """Set all targets on a blendshape node to 0 when not connected"""
    shapes = list_shapes(blendshape_name)
    for shape in shapes:
        blendshape_target = f"{blendshape_name}.{shape}"
        con = cmds.listConnections(blendshape_target, d=False, s=True, p=True)
        if con is not None:
            continue
        cmds.setAttr(blendshape_target, 0)

def reset_blendshape_target(blendshape, target):
    # type: (str, str) -> None
    shapes = list_shapes(blendshape)
    if target not in shapes:
        logger.warning(f"Shape {target} not found on blendshape {blendshape}")
        return
    blendshape_target = f"{blendshape}.{target}"
    con = cmds.listConnections(blendshape_target, d=False, s=True, p=True)
    if con is not None:
        return
    cmds.setAttr(blendshape_target, 0)

def reset_specific_blendshape_targets(blendshape_name, targets):
    # type: (str, List) -> None
    for shape in targets:
        reset_blendshape_target(blendshape_name, shape)

def activate_blendshape_target(blendshape, target):
    # type: (str, str) -> None
    shapes = list_shapes(blendshape)
    if target not in shapes:
        logger.warning(f"Shape {target} not found on blendshape {blendshape}")
        return
    blendshape_target = f"{blendshape}.{target}"
    con = cmds.listConnections(blendshape_target, d=False, s=True, p=True)
    if con is not None:
        return
    cmds.setAttr(blendshape_target, 1)

def activate_blendshape_targets(blendshape, targets):
    # type: (str, List) -> None
    for shape in targets:
        activate_blendshape_target(blendshape, shape)

def export_blendshape_targets(mesh):
    # type: (str) -> List
    blendshape_node = deformers_by_type(mesh, "blendShape")
    if not blendshape_node:
        logger.warning("No blendshape node found, terminating export_blendshape_targets...")
        return
    reset_blendshape_targets(blendshape_node[0])
    target_shapes = list_shapes(blendshape_node[0])
    shapes_grp = cmds.createNode("transform", n="shapes_GRP")
    extracted_meshes = []
    for shape in target_shapes:
        attr = f"{blendshape_node[0]}.{shape}"
        cmds.setAttr(attr, 1)
        duplicate_mesh = cmds.duplicate(mesh, n=shape)[0]
        cmds.parent(duplicate_mesh, shapes_grp)
        cmds.rename(duplicate_mesh, shape)
        extracted_meshes.append(shape)
        cmds.setAttr(attr, 0)
    return extracted_meshes

def vertex_ids_from_components_target(components_target):
    # type: (List[str]) -> List[int]
    """Returns a flattened list of vertex ids from a components target list.

    The components target list typically comes from getting the following attribute:
    f"{blendshape}.inputTarget[0].inputTargetGroup[{i}].inputTargetItem[6000].inputComponentsTarget"
    """
    verts = []
    for vert_id in components_target:
        match = re.findall(r"\d+", vert_id)
        if match:
            if len(match) == 1:
                target_index = int(match[0])
                verts.append(target_index)
            elif len(match) == 2:
                start = int(match[0])
                end = int(match[1])
                flatten = list(range(start, end + 1))
                verts.extend(flatten)
    return list(set(verts))

def get_deltas(blendshape_name):
    # type: (str) -> List[Delta]
    """Get the deltas for all targets in a blendshape node"""
    deltas = []  # type: List[Delta]
    shapes = list_shapes(blendshape_name)
    for shape in shapes:
        shape_idx = get_target_index(blendshape_name, shape)
        delta = {"name": shape, "indices": None, "deltas": None}  # type: dict
        offsets = cmds.getAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputPointsTarget".format(
                blendshape_name, shape_idx
            )
        )
        if offsets:
            offsets = [o[:3] for o in offsets]
        else:
            offsets = []
        delta["deltas"] = offsets
        vtx_indices = cmds.getAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputComponentsTarget".format(
                blendshape_name, shape_idx
            )
        )
        if not vtx_indices:
            vtx_indices = []
        indices = vertex_ids_from_components_target(vtx_indices)
        delta["indices"] = indices
        deltas.append(Delta.load(delta))
    return deltas

def get_delta(blendshape_name, target):
    # type: (str, str) -> Delta
    shape_idx = get_target_index(blendshape_name, target)
    if shape_idx < 0:
        return None
    delta = {"name": target, "indices": None, "deltas": None}  # type: dict
    offsets = cmds.getAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputPointsTarget".format(
            blendshape_name, shape_idx
        )
    )
    if offsets:
        offsets = [o[:3] for o in offsets]
    else:
        offsets = []
    delta["deltas"] = offsets
    vtx_indices = cmds.getAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputComponentsTarget".format(
            blendshape_name, shape_idx
        )
    )
    if not vtx_indices:
        vtx_indices = []
    indices = vertex_ids_from_components_target(vtx_indices)
    delta["indices"] = indices
    return Delta.load(delta)

def set_deltas(blendshape_name, deltas):
    # type: (str, List[Delta]) -> List[Delta]
    """Set the deltas for all targets in a blendshape node"""
    shapes = list_shapes(blendshape_name)
    applied_deltas = []  # type: List[Delta]
    for delta in deltas:
        if delta.name not in shapes:
            continue
        shape_idx = get_target_index(blendshape_name, delta.name)
        delta_vectors = [d for d in delta.deltas.tolist()]

        # fmt: off
        cmds.setAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputPointsTarget".format(
                blendshape_name, shape_idx
            ),
            len(delta_vectors),
            *delta_vectors,
            type="pointArray"
        )
        # fmt: on
        component_list = [f"vtx[{idx}]" for idx in delta.indices]

        # fmt: off
        cmds.setAttr(
            "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputComponentsTarget".format(
                blendshape_name, shape_idx
            ),
            len(delta.indices),
            *component_list,
            type="componentList"
        )
        # fmt: on
        applied_deltas.append(delta)

    return applied_deltas

def set_delta(blendshape_name, delta, target_name=None):
    # type: (str, Delta, Optional[str]) -> Delta
    shapes = list_shapes(blendshape_name)
    if delta.name not in shapes and target_name is None:
        print("returning None")
        return None
    if target_name is not None and target_name not in shapes:
        print("returning None")
        return None
    if target_name is not None:
        shape_idx = get_target_index(blendshape_name, target_name)
    else:
        shape_idx = get_target_index(blendshape_name, delta.name)
    delta_vectors = [d for d in delta.deltas.tolist()]

    # fmt: off
    cmds.setAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputPointsTarget".format(
            blendshape_name, shape_idx
        ),
        len(delta_vectors),
        *delta_vectors,
        type="pointArray"
    )
    # fmt: on
    component_list = [f"vtx[{idx}]" for idx in delta.indices]

    # fmt: off
    cmds.setAttr(
        "{}.inputTarget[0].inputTargetGroup[{}].inputTargetItem[6000].inputComponentsTarget".format(
            blendshape_name, shape_idx
        ),
        len(delta.indices),
        *component_list,
        type="componentList"
    )
    # fmt: on
    return delta

def get_weights_from_blendshape(blendshape_name, remove_unused_maps=False):
    # type: (str, Optional[bool]) -> List[WeightMap]
    targets = list_shapes(blendshape_name)
    target_indices = [get_target_index(blendshape_name, target) for target in targets]
    weights = []

    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    for shape_name, shape_idx in zip(targets, target_indices):
        values = cmds.getAttr(
            f"{blendshape_name}.inputTarget[0].inputTargetGroup[{shape_idx}].targetWeights[0:{vertex_count-1}]"
        )
        if all(i == 1 for i in values) and remove_unused_maps is True:
            continue
        weights.append(WeightMap(shape_name, values))
    return weights

def get_weight_from_blendshape_target(blendshape_name, target):
    # type: (str, str) -> WeightMap
    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    target_index = get_target_index(blendshape_name, target)
    values = cmds.getAttr(f"{blendshape_name}.inputTarget[0].inputTargetGroup[{target_index}].targetWeights[0:{vertex_count-1}]")
    weights = WeightMap(target, values)
    return weights

def export_weight_map(blendshape_name, target, folder_path, name_overwrite=None):
    # type: (str, str, Path, Optional[str]) -> None

    weights = get_weight_from_blendshape_target(blendshape_name, target)
    if name_overwrite is not None and isinstance(name_overwrite, str):
        new_file, _ = find_new_version(folder_path, name_overwrite, "wmap")
    else:
        new_file, _ = find_new_version(folder_path, target, "wmap")

    with open(str(new_file), "w") as f:
        json.dump(weights.data(), f)

def export_all_weight_maps(blendshape_name, folder_path):
    # type: (str, Path) -> None

    weights = get_weights_from_blendshape(blendshape_name, remove_unused_maps=True)
    for wm in weights:
        new_file, _ = find_new_version(folder_path, wm.name, "wmap")
        with open(str(new_file), "w") as f:
            json.dump(wm.data(), f)

def apply_weightmap_to_base(blendshape_name, weight_map):
    # type: (str, WeightMap) -> None
    values = weight_map.get_weights()
    target_weights_attr = (
        f"{blendshape_name}.inputTarget[0].baseWeights[0:{len(values) - 1}]"
    )
    cmds.setAttr(target_weights_attr, *values, size=len(values))

def apply_weightmap_to_target(blendshape_name, target_name, weight_map):
    # type: (str, str, WeightMap) -> None
    target_index = get_target_index(blendshape_name, target_name)
    values = weight_map.get_weights()
    target_weights_attr = f"{blendshape_name}.inputTarget[0].inputTargetGroup[{target_index}].targetWeights[0:{len(values) - 1}]"
    cmds.setAttr(target_weights_attr, *values, size=len(values))

def get_adjusted_weight_maps(blendshape_name):
    # type: (str) -> List[str]
    targets = list_shapes(blendshape_name)
    target_indices = [get_target_index(blendshape_name, target) for target in targets]
    weight_maps = []
    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    for shape_name, shape_idx in zip(targets, target_indices):
        values = cmds.getAttr(
            f"{blendshape_name}.inputTarget[0].inputTargetGroup[{shape_idx}].targetWeights[0:{vertex_count-1}]"
        )
        if np.all(np.array(values) == 1):
            continue
        weight_maps.append(shape_name)
    return weight_maps

def import_weight_map(blendshape_name, target, file_path):
    # type: (str, str, Path) -> None
    with open(str(file_path), "r") as f:
        data = json.load(f)

    weight_map = WeightMap.load(data)

    apply_weightmap_to_target(blendshape_name, target, weight_map)

def get_all_blendshapes():
    # type: () -> List[str]
    all_blendshapes = []
    meshes = get_all_meshes()
    for mesh in meshes:
        blendshapes = deformers_by_type(mesh, "blendShape")
        if not blendshapes:
            continue
        all_blendshapes.extend(blendshapes)

    return all_blendshapes


def normalize_weight_maps(blendshape, targets):
    # type: (str, List) -> None
    weights_dict = {}
    output = []
    
    for target in targets:
        mesh = cmds.blendShape(blendshape, q=True, geometry=True)
        verticies = cmds.ls(mesh[0] + ".vtx[*]", fl=True)
        target_index = get_target_index(blendshape, target)
        for vertex in verticies:
            vtx = vertex.split(".")[1]
            index = re.findall(r"[0-9]+", vtx)
            weight = cmds.getAttr("{}.inputTarget[0].inputTargetGroup[{}].targetWeights[{}]".format(blendshape, target_index, index[0]))
            if vertex not in weights_dict:
                weights_dict[vertex] = [weight]
            else:
                weights_dict[vertex].append(weight)
                
    
    for key, values in weights_dict.items():
        
        vtx = key.split(".")[1]
        index = re.findall(r"[0-9]+", vtx)
        
        total_weight_per_vertex = sum(values)
        if total_weight_per_vertex != 1 and total_weight_per_vertex != 0:
            output.append([key, total_weight_per_vertex])
            normalizer = 1 / float( sum(values) )
            numListNormalized = [x * normalizer for x in values]
            output.append("vertex: {}\norg_values: {}, org_total_weight: {}\nnew_values: {}, new_total_weight: {}".format(
                key,
                values,
                total_weight_per_vertex,
                numListNormalized,
                sum(numListNormalized)
            ))
            
            for idx, target in enumerate(targets):
                target_index = get_target_index(blendshape, target)
                cmds.setAttr("{}.inputTarget[0].inputTargetGroup[{}].targetWeights[{}]".format(blendshape, idx, index[0]), numListNormalized[idx])
                        
    if not output:
        print("All weights add up to 1")
        return
        
    output_str = "The following verticies have been normalized:"
    for value in output:
        output_str += "\n\n{}".format(value)
        
    print(output_str)

def normalize_default_weight_maps(blendshape):
    # type: (str) -> None
    default_splitting_data = {
        "four_split_targets": [
            "msk_xUpperLeft",
            "msk_xUpperRight",
            "msk_xDownLeft",
            "msk_xDownRight"
        ],

        "left_right_targets": [
            "msk_xLeft",
            "msk_xRight"
        ],

        "upper_down_targets": [
            "msk_xUpper",
            "msk_xDown"
        ],
    }

    for targets in default_splitting_data.values():
        normalize_weight_maps(blendshape, targets)

def create_corrective_delta(blendshape, full_shapes, corrective):
    # type: (str, List, str) -> Delta
    # full_shape_delta = [get_delta(blendshape, x) for x in full_shapes]
    # full_sum = None
    # for i in full_shape_delta:
    #     print(full_sum)
    #     if full_sum is None:
    #         full_sum = i
    #         continue
    #     full_sum = full_sum + i
    # target_corrective_delta = get_delta(blendshape, corrective)
    # final_corrective_delta = target_corrective_delta - full_sum

    # set_delta(blendshape, final_corrective_delta, target_name=corrective)
    
    # check_delta = final_corrective_delta == target_corrective_delta
    # print(check_delta)

    # return final_corrective_delta

    mesh = cmds.blendShape(blendshape, q=True, geometry=True)[0]
    dummy_mesh = cmds.duplicate(mesh, n="splitting_mesh")[0]

    reset_blendshape_targets(blendshape)

    activate_blendshape_target(blendshape, corrective)

    corrective_shape = cmds.duplicate(mesh, name=f"{corrective}_corrective")[0]

    reset_blendshape_target(blendshape, corrective)

    activate_blendshape_targets(blendshape, full_shapes)

    extracted_delta = ExtractCorrectiveDelta.calculate(mesh, corrective_shape)

    dummy_bsn = cmds.blendShape(extracted_delta, dummy_mesh)

    cmds.rename(extracted_delta, corrective)

    # return delta

