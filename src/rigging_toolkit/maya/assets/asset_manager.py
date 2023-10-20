from maya import cmds
from rigging_toolkit.core.context import Context
from rigging_toolkit.core.filesystem import find_latest, find_new_version
from typing import Optional, List
import re
from rigging_toolkit.maya.utils import export_mesh, get_all_transforms

def import_character_assets(context, ignore_list=None):
    # type: (Context, Optional[List[str]]) -> None
    for asset in context.assets_path.iterdir():
        if ignore_list:
            if not asset.name in ignore_list:
                continue
        path = asset / "meshes"
        name = f"geo_{asset.name}_L1"
        latest, _ = find_latest(path, name, "abc")
        cmds.file(str(latest), i=True, uns=False)

def export_character_assets(context, assets):
    # type: (Context, List[str]) -> None
    asset_pattern = r'^geo_(\w+)_L1$'
    character_assets_path = context.assets_path

    for asset in assets:
        if not cmds.objExists(asset):
            continue
        match = re.match(asset_pattern, asset)
        if match:
            asset_name = match.group(1)

            asset_path = character_assets_path / asset_name / "meshes"

            new_version, _ = find_new_version(asset_path, asset, "abc")

            export_mesh(asset, new_version)

def export_all_character_assets(context):
    # type: (Context) -> None
    assets = get_all_transforms()
    export_character_assets(context, assets)

def export_selected_character_assets(context):
    # type: (Context) -> None
    assets = cmds.ls(sl=1)
    export_character_assets(context, assets)








