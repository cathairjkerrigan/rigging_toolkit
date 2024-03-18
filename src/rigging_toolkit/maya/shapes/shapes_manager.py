from maya import cmds
from typing import Optional, List, Dict, Generator
from rigging_toolkit.core.context import Context
from rigging_toolkit.core.filesystem import find_latest, find_new_version, Path
from rigging_toolkit.maya.utils import export_blendshape_targets, ls, export_versioned_mesh, import_asset, ExtractCorrectiveDelta, ls_all
import json
import logging
from copy import copy
from .splitter import Splitter
from .base import Plug, ConnectTypes, Socket
from contextlib import contextmanager
import re


logger = logging.getLogger(__name__)

def export_shapes(context):
    # type: (Context) -> None
    pattern = re.compile(r'^shp_.*L\d+$')

    shapes = [element for element in ls_all() if pattern.match(element)]

    for shape in shapes:

        shp_folder = Path.validate_path(context.shapes_path / shape, create_missing=True)
        
        export_versioned_mesh(shape, shp_folder)

def export_blendshapes(context, split_type=None):
    # type: (Context, Optional[str]) -> None
    mesh = ls()
    if not mesh:
        return
    blendshape_targets = export_blendshape_targets(mesh[0])
    for shape in blendshape_targets:
        if split_type:
            shp_folder = Path.validate_path(context.shapes_path / split_type / shape, create_missing=True)
        else:
            shp_folder = Path.validate_path(context.shapes_path / shape, create_missing=True)
        
        export_versioned_mesh(shape, shp_folder)

def import_shapes(context, ignore_list=None):
    # type: (Context, Optional[List]) -> List[str]
    shapes = []
    grp = cmds.createNode("transform", n="full_shapes_GRP")
    for shp_path in context.shapes_path.iterdir():
        if ignore_list is not None and shp_path.stem in ignore_list:
            logger.warning(f"Ignoring {shp_path.stem} for import...")
            continue
        latest, _ = find_latest(shp_path, shp_path.stem,  "abc")
        shp = import_asset(latest)[0]
        cmds.parent(shp, grp)
        shapes.append(shp)
    return shapes

def import_head(context):
    # type: (Context) -> List[str]
    head_asset_path = context.assets_path / "head" / "meshes"
    latest, _ = find_latest(head_asset_path, "geo_head_L1",  "abc")
    asset = import_asset(latest)[0]
    return asset

def create_deltas(head, shapes):
    # type: (str, str) -> List[str]
    pass

def build_face_rig_shapes(context):
    # type: (Context) -> None
    full_shapes = import_shapes(context)
    head = import_head(context)
    # create_deltas(shapes)

