from maya import cmds
from typing import List, Optional
import re
from rigging_toolkit.maya.utils.deformers.general import deformers_by_type
from rigging_toolkit.maya.utils.delta import Delta
from rigging_toolkit.maya.utils.weightmap import WeightMap
from rigging_toolkit.core.filesystem import find_new_version
from rigging_toolkit.maya.utils.mesh_utils import get_all_meshes, mirror_vertex_by_pos, mirror_vertices_by_edge
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

def export_blendshape_targets_to_grp(mesh):
    # type: (str) -> str
    shapes_grp = cmds.createNode("transform", n=f"{mesh})_Shapes_GRP")
    blendshapes = export_blendshape_targets(mesh)
    cmds.parent(blendshapes, shapes_grp)
    return shapes_grp

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

def get_weights_from_blendshape_target(blendshape_name, target):
    # type: (str, str) -> WeightMap
    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    target_index = get_target_index(blendshape_name, target)
    values = cmds.getAttr(f"{blendshape_name}.inputTarget[0].inputTargetGroup[{target_index}].targetWeights[0:{vertex_count-1}]")
    weights = WeightMap(target, values)
    return weights

def export_weight_map(blendshape_name, target, folder_path, name_overwrite=None):
    # type: (str, str, Path, Optional[str]) -> None

    weights = get_weights_from_blendshape_target(blendshape_name, target)
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

# Not really worth using, too slow
def get_adjusted_weight_maps(blendshape_name):
    # type: (str) -> List[str]
    adjusted_maps = []
    weight_maps = get_weights_from_blendshape(blendshape_name)
    vertex_count = weight_maps[0].vertex_count
    default_wm = WeightMap.load_default("default", vertex_count)
    for weight_map in weight_maps:
        if default_wm == weight_map:
            continue
        adjusted_maps.append(weight_map)
    
    return adjusted_maps

def import_weight_map(blendshape_name, target, file_path):
    # type: (str, str, Path) -> None
    with open(str(file_path), "r") as f:
        data = json.load(f)

    weight_map = WeightMap.load(data)

    apply_weightmap_to_target(blendshape_name, target, weight_map)

def import_weight_map_to_targets(blendshape_name, targets, file_path):
    # type: (str, List[str], Path) -> None
    with open(str(file_path), "r") as f:
        data = json.load(f)

    weight_map = WeightMap.load(data)
    for target in targets:
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

def apply_default_weightmap_to_target(blendshape_name, target_name):
    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    default_weightmap = WeightMap.load_default(name=target_name, vertex_count=vertex_count)
    apply_weightmap_to_target(blendshape_name, target_name, default_weightmap)
    return default_weightmap

def create_corrective_delta(blendshape, full_shapes, corrective):

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

def set_delta_weightmap_to_target(blendshape_name, target):
    default_weight_map = apply_default_weightmap_to_target(blendshape_name, target)
    delta = get_delta(blendshape_name, target)
    data = delta.data()

    indicies = data["indices"]
    target_index = get_target_index(blendshape_name, target)
    mesh = cmds.blendShape(blendshape_name, q=True, geometry=True)
    vertex_count = cmds.polyEvaluate(mesh, v=True)
    for idx in range(0, vertex_count):
        target_weights_attr = f"{blendshape_name}.inputTarget[0].inputTargetGroup[{target_index}].targetWeights[{idx}]"
        if idx in indicies:
            cmds.setAttr(target_weights_attr, 1.0)
            continue
        cmds.setAttr(target_weights_attr, 0.0)

    weight_map = get_weights_from_blendshape_target(blendshape_name, target)
    return weight_map

def inverse_target_weightmap(blendshape_name, target):
    weights = get_weights_from_blendshape_target(blendshape_name, target)
    inverse_weights = weights.inverse()
    apply_weightmap_to_target(blendshape_name, target, inverse_weights)

def get_transform_from_blendshape(blendshape_name):
    # type: (str) -> str
    shape = cmds.blendShape(blendshape_name, q=True, geometry=True)[0]
    transform = cmds.listRelatives(shape, typ="transform", p=True)[0]
    return transform

def mirror_weight_map_by_pos(blendshape_name, target, mirror_type="world", mirror_axis="x"):
    # type: (str, str, Optional[str], Optional[str]) -> WeightMap
    mesh = get_transform_from_blendshape(blendshape_name)
    current_weight_map = get_weights_from_blendshape_target(blendshape_name, target)
    current_weights = current_weight_map.weights
    indicies = current_weight_map.indices
    mirrored_weights_dict = {}
    mirrored_values = []
    for idx, weight in current_weights.items():
        mirrored_idx = mirror_vertex_by_pos(mesh, idx, mirror_axis, mirror_type)
        mirrored_weights_dict[mirrored_idx] = weight

    non_mirrored_verticies = []

    for vtx in indicies:
        vtx_weights = mirrored_weights_dict.get(vtx)
        if vtx_weights is None:
            vtx_weights = 0.0
            non_mirrored_verticies.append(vtx)
        mirrored_values.append(vtx_weights)

    mirrored_weight_map = WeightMap(f"{current_weight_map.name}_mirrored", mirrored_values)
    apply_default_weightmap_to_target(blendshape_name, target)
    initial_delta = get_delta(blendshape_name, target)
    new_target_name = f"{initial_delta.name}_mirrored"
    duplicate_blendshape_target(blendshape_name, target, new_name=new_target_name)
    set_delta(blendshape_name, initial_delta, new_target_name)
    apply_weightmap_to_target(blendshape_name, target, current_weight_map)
    apply_weightmap_to_target(blendshape_name, new_target_name, mirrored_weight_map)

    if non_mirrored_verticies:
        logger.warning(
            "The following vertex weights have not been mirrored, please check mesh symmetry"
        )
        logger.warning(f"{non_mirrored_verticies}")

    return mirrored_weight_map

def mirror_weight_map_by_topology(blendshape_name, target, mirror_edge):
    # type: (str, str, str) -> WeightMap
    mesh = get_transform_from_blendshape(blendshape_name)
    current_weight_map = get_weights_from_blendshape_target(blendshape_name, target)
    current_weights = current_weight_map.weights
    indicies = current_weight_map.indices
    match = re.search(r'\[(\d+)\]', mirror_edge)

    if match:
        edge = int(match.group(1))

    mirrored_weights = []
    mirrored_vertices = mirror_vertices_by_edge(mesh, edge, indicies)
    for idx in mirrored_vertices:
        current_weight = current_weights.get(idx)
        mirrored_weights.append(current_weight)

    mirrored_weight_map = WeightMap(f"{current_weight_map.name}_mirrored", mirrored_weights)
    apply_default_weightmap_to_target(blendshape_name, target)
    initial_delta = get_delta(blendshape_name, target)
    new_target_name = f"{initial_delta.name}_mirrored"
    duplicate_blendshape_target(blendshape_name, target, new_name=new_target_name)
    set_delta(blendshape_name, initial_delta, new_target_name)

    apply_weightmap_to_target(blendshape_name, target, current_weight_map)
    apply_weightmap_to_target(blendshape_name, new_target_name, mirrored_weight_map)

    return mirrored_weight_map

def mirror_weight_map_by_topology_selection(blendshape_name, target):

    mesh = get_transform_from_blendshape(blendshape_name)

    cmds.select(cl=True)
    cmds.selectMode(co=True)
    cmds.selectType(eg=True)
    cmds.hilite(mesh, r=True)
    cmds.inViewMessage(amg='<hl>Select Center Edge</hl>.', pos='topCenter', fade=True )

    def mirror_weight_map_callback(blendshape_name, target):
        logger.info("Selection changed. Calling mirror_weight_map_by_topology...")
        mirror_weight_map_by_topology(blendshape_name, target, cmds.ls(sl=True)[0])

    cmds.scriptJob(runOnce=True, e=("SelectionChanged", lambda: mirror_weight_map_callback(blendshape_name, target)))

def combine_weight_maps(blendshape, targets):
    # type: (str, List[str]) -> WeightMap
    weightmaps = [get_weights_from_blendshape_target(blendshape, x) for x in targets]
    initial_delta = get_delta(blendshape, targets[0])
    new_target_name = f"{initial_delta.name}_combined"
    duplicate_blendshape_target(blendshape, targets[0], new_target_name)
    set_delta(blendshape, initial_delta, new_target_name)
    combined_weightmap = WeightMap.combine(weightmaps)
    apply_weightmap_to_target(blendshape, new_target_name, combined_weightmap)
    return combined_weightmap

def subtract_weight_maps(blendshape, targets):
    # type: (str, List[str]) -> WeightMap
    weightmaps = [get_weights_from_blendshape_target(blendshape, x) for x in targets]
    initial_delta = get_delta(blendshape, targets[0])
    new_target_name = f"{initial_delta.name}_subtracted"
    duplicate_blendshape_target(blendshape, targets[0], new_target_name)
    set_delta(blendshape, initial_delta, new_target_name)
    subtracted_weightmap = WeightMap.difference(weightmaps)
    apply_weightmap_to_target(blendshape, new_target_name, subtracted_weightmap)
    return subtracted_weightmap

def duplicate_blendshape_target(blendshape, target, new_name=""):
    # type: (str, str, Optional[str]) -> str
    reset_blendshape_targets(blendshape)
    cmds.setAttr(f"{blendshape}.{target}", 1)
    transform = get_transform_from_blendshape(blendshape)
    if new_name:
        new_transform = cmds.duplicate(transform, n=new_name)[0]
    else:
        new_transform = cmds.duplicate(transform, n=f"{target}_duplicate")[0]

    add_blendshape_target(blendshape, new_transform)

    cmds.delete(new_transform)

    return new_transform
