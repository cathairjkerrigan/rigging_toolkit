from maya import cmds
from rigging_toolkit.maya.utils import import_node_network, export_node_network, get_shaders_from_meshes, assign_shader
from rigging_toolkit.core import Context, find_new_version, find_file, find_latest
from dataclasses import dataclass, field, asdict, fields
from typing import List, Dict, Optional
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

DEBUG = True

# come back to this -- would be useful for dealing with shader information, could be overkill though

# @dataclass
# class Shader:

#     name: str = field(default="")
#     data: Dict = field(default=dict)

#     @classmethod
#     def export_shaders(cls, meshes, file_path):
#         # type: (List[str], Path) -> None
#         shaders = get_shaders_from_meshes(meshes)
#         for shader in shaders:
#             path = file_path / f"{shader}.json"
#             export_node_network(shader, path)

#     @classmethod
#     def import_shaders(cls, file_path):
#         pass


def export_shaders(meshes, file_path):
    # type: (List[str], Path) -> None
    shaders = get_shaders_from_meshes(meshes)
    for shader in shaders:
        path, _ = find_new_version(file_path, shader, "json")
        if DEBUG: logger.info(f"export shaders: shader -- {shader} | file_path -- {str(path)}")
        export_node_network(shader, path)

def import_shader(file_path, meshes=None, name_overwrite=None):
    # type: (Path, Optional[List[str]], Optional[str]) -> None
    import_node_network(file_path)
    if meshes is not None:
        shader = name_overwrite if name_overwrite else file_path.stem
        for mesh in meshes:
            assign_shader(mesh=mesh, shader=shader)

def setup_shaders(context):
    # type: (Context) -> None
    shader_json = find_file(context.config_path, "setup_shaders", "json")
    with open(str(shader_json)) as f:
        setup_data = json.load(f)

    for shader, meshes in setup_data.items():
        shader_file, _ = find_latest(context.shaders_path, shader, "json")
        import_shader(shader_file, meshes, name_overwrite=shader)

