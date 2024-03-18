from maya import cmds
from typing import Optional, List
from rigging_toolkit.core.filesystem import Path
from rigging_toolkit.core.filesystem import find_latest_partial, find_file

        
class Material(object):
    
    def __init__(self, name, texture_file):
        # type: (str, Path) -> None

        self._connect_attrs = [
		("coverage", "coverage"),			  
        ("mirrorU", "mirrorU"),
        ("mirrorV", "mirrorV"),
        ("noiseUV", "noiseUV"),
        ("offset", "offset"),
        ("outUV", "uvCoord"),
        ("outUvFilterSize", "uvFilterSize"),
        ("repeatUV", "repeatUV"),
        ("rotateFrame", "rotateFrame"),
        ("rotateUV", "rotateUV"),
        ("stagger", "stagger"),
        ("translateFrame", "translateFrame"),
        ("vertexCameraOne", "vertexCameraOne"),
        ("vertexUvOne", "vertexUvOne"),
        ("vertexUvThree", "vertexUvThree"),
        ("vertexUvTwo", "vertexUvTwo"),
        ("wrapU", "wrapU"),
        ("wrapV", "wrapV"),
        ]
        
        self.name = name
        self.texture_file = texture_file
        
        self.texture_node = cmds.createNode("place2dTexture", n=f"{self.name}_place2dTexture")
        self.file_node = cmds.createNode("file", n=f"{self.name}_file")
        self.create_connections()
        self.set_file_path(self.texture_file)
        
    def set_file_path(self, texture_file):
        # type: (Path) -> None

        cmds.setAttr(f"{self.file_node}.fileTextureName", str(texture_file), typ="string")
        
    def create_connections(self):
        # type: () -> None

        for connection in self._connect_attrs:
            cmds.connectAttr(f"{self.texture_node}.{connection[0]}", f"{self.file_node}.{connection[1]}", force=True)
            
    def set_color_space(self, color_space):
        # type: (str) -> None

        cmds.setAttr(f"{self.file_node}.colorSpace", color_space, typ="string")
        
    def set_alpha_luminance(self, value):
        # type: (int) -> None

        cmds.setAttr(f"{self.file_node}.alphaIsLuminance", value)
        
        
class PBRShader(object):
    
    def __init__(
        self,
        name, # type: str
        base_color_path, # type: Path
        metalic_path, # type: Path
        roughness_path, # type: Path
        normal_path, # type: Path
        meshes=None # type: Optional[List[str]]
        ):
        
        self.name = name
        self.base_color = Material(name=f"{self.name}_baseColor", texture_file=base_color_path)
        self.metalic = Material(name=f"{self.name}_metalic", texture_file=metalic_path)
        self.roughness = Material(name=f"{self.name}_roughness", texture_file=roughness_path)
        self.normal = Material(name=f"{self.name}_normal", texture_file=normal_path)
        
        self.standardSurfaceMaterial = cmds.shadingNode('aiStandardSurface', asShader=True, name=f"{name}_aiStandardSurface")
        self.shading_group = cmds.sets(renderable=True, noSurfaceShader=True, empty=True)
        
        self.create_connections()
        
        if meshes:
            self.assign_materials(meshes)
        
    def create_connections(self):
        # type: () -> None

        self.connect_base_color()
        self.connect_metalic()
        self.connect_roughness()
        self.connect_normal()
        self.connect_shader()
        
    def connect_base_color(self):
        # type: () -> None

        base_color_file_node = self.base_color.file_node
        
        cmds.connectAttr(f"{base_color_file_node}.outColor", f"{self.standardSurfaceMaterial}.baseColor")
        
    def connect_metalic(self):
        # type: () -> None

        self.metalic.set_color_space("Raw")
        self.metalic.set_alpha_luminance(1)
        metalic_file_node = self.metalic.file_node
        
        cmds.connectAttr(f"{metalic_file_node}.outAlpha", f"{self.standardSurfaceMaterial}.metalness")
        
    def connect_roughness(self):
        # type: () -> None

        self.roughness.set_color_space("Raw")
        self.roughness.set_alpha_luminance(1)
        roughness_file_node = self.roughness.file_node
        
        cmds.connectAttr(f"{roughness_file_node}.outAlpha", f"{self.standardSurfaceMaterial}.specularRoughness")
        
    def connect_normal(self):
        # type: () -> None

        self.normal.set_color_space("Raw")
        normal_file_node = self.normal.file_node
        
        bump_node = cmds.createNode("bump2d", n=f"{self.name}_bump2d")
        cmds.setAttr(f"{bump_node}.bumpInterp", 1)
        
        cmds.connectAttr(f"{normal_file_node}.outAlpha", f"{bump_node}.bumpValue")
        cmds.connectAttr(f"{bump_node}.outNormal", f"{self.standardSurfaceMaterial}.normalCamera")
        
    def connect_shader(self):
        # type: () -> None

        cmds.connectAttr(f"{self.standardSurfaceMaterial}.outColor", f"{self.shading_group}.surfaceShader")
        
    def assign_materials(self, meshes):
        # type: (List) -> None

        for mesh in meshes:
            if not cmds.objExists(mesh):
                continue
            cmds.select(mesh, r=True)
            cmds.hyperShade(assign=self.standardSurfaceMaterial)
            cmds.select(cl=True)