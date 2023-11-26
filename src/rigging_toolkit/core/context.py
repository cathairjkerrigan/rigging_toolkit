from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import re
from rigging_toolkit.core.filesystem import validate_path, path_exists

@dataclass(frozen=True,order=True)
class Context:

    project_path: Path = field(default=Path)
    character_name: str = field(default="")
    assets_series: int = field(default=int)
    rigs_series: int = field(default=int)
    texture_series: int = field(default=int)
    shapes_series: int = field(default=int)
    utilities_series: int = field(default=int)
    animation_series: int = field(default=int)
    build_series: int =  field(default=int)
    shaders_series: int = field(default=int)
    config_path: Path = field(default=Path)

    @classmethod
    def new(
        cls,
        project_path, # type: Path
        character_name, # type: str
        assets_series = None, # type: Optional[int]
        rigs_series = None, # type: Optional[int]
        texture_series = None, # type: Optional[int]
        shapes_series = None, # type: Optional[int]
        utilities_series = None, # type: Optional[int]
        animation_series = None, # type: Optional[int]
        build_series = None, # type: Optional[int]
        shaders_series = None, # type: Optional[int]
        config_path = None, # type: Optional[Path]
        create_context = False # type: Optional[bool]
    ):

        project_path = validate_path(project_path, create_missing=create_context)
        character_path = validate_path(project_path / character_name, create_missing=create_context)

        wip_path = validate_path(character_path / "wip", create_missing=create_context)

        if config_path is None and wip_path:
            config_path = validate_path(wip_path / ".config", create_missing=create_context)

        series_match = re.compile("\d\d\d")

        if create_context:
            default_series = 100
        else:
            default_series = -1

        if assets_series is None and wip_path:
            assets_path = validate_path(wip_path / "assets", create_missing=create_context)
            if assets_path:
                series = [
                    f.name for f in assets_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    assets_series = default_series
                else:
                    assets_series = max(map(int, series))

                validate_path(assets_path / str(assets_series), create_missing=create_context)

                
        if rigs_series is None and wip_path:
            rigs_path = validate_path(wip_path / "rigs", create_missing=create_context)
            if rigs_path:
                series = [
                    f.name for f in rigs_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    rigs_series = default_series
                else:
                    rigs_series = max(map(int, series))

                validate_path(rigs_path / str(rigs_series), create_missing=create_context)
        
        if texture_series is None and wip_path:
            texture_path = validate_path(wip_path / "textures", create_missing=create_context)
            if texture_path:
                series = [
                    f.name for f in texture_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    texture_series = default_series
                else:
                    texture_series = max(map(int, series))

                validate_path(texture_path / str(texture_series), create_missing=create_context)
        
        if shapes_series is None and wip_path:
            shapes_path = validate_path(wip_path / "shapes", create_missing=create_context)
            if shapes_path:
                series = [
                    f.name for f in shapes_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    shapes_series = default_series
                else:
                    shapes_series = max(map(int, series))

                validate_path(shapes_path / str(shapes_series), create_missing=create_context)

        if utilities_series is None and wip_path:
            utilities_path = validate_path(wip_path / "utilities", create_missing=create_context)
            if utilities_path:
                series = [
                    f.name for f in utilities_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    utilities_series = default_series
                else:
                    utilities_series = max(map(int, series))

                validate_path(utilities_path / str(utilities_series), create_missing=create_context)

        if animation_series is None and project_path:
            animation_path = validate_path(project_path / character_name / "animation", create_missing=create_context)
            if animation_path:
                series = [
                    f.name for f in animation_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    animation_series = default_series
                else:
                    animation_series = max(map(int, series))

                validate_path(animation_path / str(animation_series), create_missing=create_context)
        
        if build_series is None and project_path:
            build_path = validate_path(project_path / character_name / "builds", create_missing=create_context)
            if build_path:
                series = [
                    f.name for f in build_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    build_series = default_series
                else:
                    build_series = max(map(int, series))

                validate_path(build_path / str(build_series), create_missing=create_context)

        if shaders_series is None and wip_path:
            shaders_path = validate_path(wip_path / "shaders", create_missing=create_context)
            if shaders_path:
                series = [
                    f.name for f in shaders_path.iterdir() if series_match.match(f.name)
                ]
                if not series:
                    shaders_series = default_series
                else:
                    shaders_series = max(map(int, series))

                validate_path(shaders_path / str(shaders_series), create_missing=create_context)

        return Context(
            project_path=project_path,
            character_name = character_name,
            assets_series = assets_series,
            rigs_series = rigs_series,
            texture_series = texture_series,
            shapes_series = shapes_series,
            utilities_series = utilities_series,
            build_series=build_series,
            animation_series=animation_series,
            shaders_series=shaders_series,
            config_path=config_path
        )
    
    @property
    def character_path(self):
        # type: () -> Path
        if self.project_path:
            return validate_path(self.project_path / self.character_name)
        return None
        
    @property
    def wip_path(self):
        # type: () -> Path
        if self.character_path:
            return validate_path(self.character_path / "wip")
        return None
    
    @property
    def assets_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "assets" / str(self.assets_series))
        return None
    
    @property
    def rigs_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "rigs" / str(self.rigs_series))
        return None
    
    @property
    def texture_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "textures" / str(self.utilities_series))
        return None
    
    @property
    def shapes_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "shapes" / str(self.shapes_series))
        return None
    
    @property
    def utilities_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "utilities" / str(self.utilities_series))
        return None
    
    @property
    def builds_path(self):
        # type: () -> Path
        if self.character_path:
            return validate_path(self.character_path / "builds" / str(self.build_series))
        return None
    
    @property
    def animation_path(self):
        # type: () -> Path
        if self.character_path:
            return validate_path(self.character_path / "animation" / str(self.animation_series))
        return None
    
    @property
    def shaders_path(self):
        # type: () -> Path
        if self.wip_path:
            return validate_path(self.wip_path / "shaders" / str(self.shaders_series))
        return None
    
    @property
    def is_valid(self):
        if not path_exists(self.project_path):
            return False
        if not self.character_name:
            return False
        if not path_exists(self.character_path):
            return False
        if self.animation_series and self.animation_series < 0:
            return False
        if not path_exists(self.animation_path):
            return False
        if self.assets_series and self.assets_series < 0:
            return False
        if not path_exists(self.assets_path):
            return False
        if self.rigs_series and self.rigs_series < 0:
            return False
        if not path_exists(self.rigs_path):
            return False
        if self.build_series and self.build_series < 0:
            return False
        if not path_exists(self.builds_path):
            return False
        if not path_exists(self.wip_path):
            return False
        if self.shaders_series and self.shaders_series < 0:
            return False
        if not path_exists(self.shaders_path):
            return False
        if self.shapes_series and self.shapes_series < 0:
            return False
        if not path_exists(self.assets_path):
            return False
        if self.texture_series and self.texture_series < 0:
            return False
        if not path_exists(self.texture_path):
            return False
        if self.utilities_series and self.utilities_series < 0:
            return False
        if not path_exists(self.utilities_path):
            return False
        if not path_exists(self.config_path):
            return False

        return True
    