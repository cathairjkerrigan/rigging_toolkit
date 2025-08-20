import json
from rigging_toolkit.core.filesystem import find_latest_partial, find_file
from rigging_toolkit.core.context import Context
from rigging_toolkit.maya.shaders.materials import PBRShader

def setup_pbr_textures(context):
    # type: (Context) -> None

    texture_path = context.texture_path

    setup_json = find_file(context.config_path, "setup_textures", "json")

    print(setup_json)

    with open(str(setup_json)) as f:
        setup_data = json.load(f)

    for material, values in setup_data.items():

        texture_folder = texture_path / material

        color_map, _ = find_latest_partial(texture_folder, "color", "png")
        metalic_map, _ = find_latest_partial(texture_folder, "metallic", "png")
        normal_map, _ = find_latest_partial(texture_folder, "normal", "png")
        roughness_map, _ = find_latest_partial(texture_folder, "roughness", "png")

        texture_name = values["name"]

        meshes = values["meshes"]

        PBRShader(
            name=texture_name,
            base_color_path=color_map,
            metalic_path=metalic_map,
            normal_path=normal_map,
            roughness_path=roughness_map,
            meshes=meshes
        )

        








    