from typing import Dict, List, Tuple

import json
import logging

from dataclasses import dataclass
import maya.cmds as cmds
import maya.mel as mel
from pathlib import Path

from rigging_toolkit.core.filesystem import find_latest
from rigging_toolkit.maya.utils.deformers.blendshape import apply_weightmap_to_base
from rigging_toolkit.maya.utils import WeightMap, has_uvset, set_current_uvset

logger = logging.getLogger(__name__)


@dataclass
class Splitter(object):
    neutral_mesh = ""  # type: str
    utility_series = None  # type: int
    project_folder = None  # type: Path

    _masks = False # type: Dict[str, Path]
    _mask_data = False  # type: Dict[str, Tuple[str, str]]

    def __attrs_post_init__(self):
        # type:() -> None
        self.masks = self._get_masks()

        # map the actual mask files to their name
        mask_map = {}
        for m in self.masks:
            # get the xDown part of msk_xDown.v001.iff
            name = m.name.split("_")[1].split(".")[0]
            if name not in mask_map:
                mask_map[name] = m
        self.mask_map = mask_map

        # create a blendshape for each mask we use, and apply the mask to it
        self._mask_data = {}
        # set uvset to utility if mesh has that
        prev_uvset = None
        has_utility_uvs = has_uvset(self.neutral_mesh, "utility")
        if has_utility_uvs:
            logger.info(f"Using utility UVSET from {self.neutral_mesh} for splitting!")
            prev_uvset = cmds.polyUVSet(self.neutral_mesh, query=True, cuv=True)[0]
            set_current_uvset(self.neutral_mesh, "utility")
        for mask_file in self.masks:
            # get the xDown part of msk_xDown.v001.iff
            mask = mask_file.name.split("_")[1].split(".")[0]
            neutral_copy = cmds.duplicate(self.neutral_mesh, name=mask + "_mesh")[0]
            blendshape = cmds.blendShape(neutral_copy, name=mask + "_blendshape")[0]
            if mask_file.suffix == ".iff":
                self._apply_mask_to_blendshape(
                    neutral_copy, blendshape, str(mask_map[mask])
                )
            elif mask_file.suffix == ".wmap":
                weight_map = None
                with open(str(mask_file), "r") as mfile:
                    mdata = json.load(mfile)
                    weight_map = WeightMap.load(mdata)
                apply_weightmap_to_base(blendshape, weight_map)
            self._mask_data[mask] = (neutral_copy, blendshape)
        if prev_uvset:
            set_current_uvset(self.neutral_mesh, prev_uvset)

    def _apply_mask_to_blendshape(self, mesh, blendshape, mask):
        # type: (str, str, str) -> None
        cmds.select(mesh)
        mel.eval(
            'artSetToolAndSelectAttr( "artAttrCtx", "blendShape.{0}.baseWeights" );'.format(
                blendshape
            )
        )
        mel.eval("artAttrBlendShapeToolScript( 4 )")
        ctx = cmds.currentCtx()
        cmds.artAttrCtx(
            ctx, e=True, ifl=mask, ifm="luminance", selectedattroper="absolute"
        )
        cmds.setToolTo("selectSuperContext")

    def _get_masks(self):
        # type: () -> List[Path]

        # TODO: find a way to get this list dynamically, either through config
        # per project, or by implementing a find_latest supporting wildcards and
        # returning a list of files instead of a single file.
        mask_names = [
            "msk_xDown",
            "msk_xDownLeft",
            "msk_xDownRight",
            "msk_xLeft",
            "msk_xRight",
            "msk_xUpper",
            "msk_xUpperLeft",
            "msk_xUpperRight",
            "msk_xLowerLidLeft",
            "msk_xLowerLidRight",
            "msk_xUpperLidLeft",
            "msk_xUpperLidRight",
        ]

        def find_masks(folder, extension):
            # type: (Path, str) -> List[Path]
            """utility function to find masks in a given folder"""
            files = []  # type: List[Path]
            for mask_name in mask_names:
                latest, version = find_latest(folder, mask_name, extension)
                if latest:
                    files.append(latest)
            return files

        asset_name = self.neutral_mesh.split("_")[1]

        # first we look for asset specific .wmap files

        mask_folder = R"{}\wip\utilities\{}\masks_{}\shape_splitter".format(
            self.project_folder, self.utility_series, asset_name
        )

        files = find_masks(Path(mask_folder), "wmap")
        if len(files) > 0:
            logger.info(f"Using {asset_name} specific .wmap masks for splitting")
            return files

        logger.debug(f"Could not find {asset_name} specific .wmap masks for splitting.")

        # ok, then look for asset specific .iff files instead

        files = find_masks(Path(mask_folder), "iff")
        if len(files) > 0:
            logger.info(f"Using {asset_name} specific .iff masks for splitting")
            return files

        logger.debug(f"Could not find {asset_name} specific .iff masks for splitting.")

        # still nothing? then look for generic .iff files instead
        # these are always in iff format as wmap files are topology specific.

        mask_folder = R"{}\wip\utilities\{}\masks\shape_splitter".format(
            self.project_folder, self.utility_series
        )

        files = find_masks(Path(mask_folder), "iff")
        if len(files) > 0:
            logger.info("Using generic .iff masks for splitting")
            return files

        logger.error("Could not locate suitable masks for splitting!")

        return []

    def split(self, shape, splits):
        # type: (str, List[str]) -> List[str]
        split_meshes = []

        # for each defined split on this shape, add it as a target to the blendshape for this split mask,
        # set it's weight to 1, duplicate the resulting mesh and remove the target again
        for split in splits:
            neutral, blendshape = self._mask_data[split]

            parts = shape.split("_")
            parts.insert(-1, split)
            split_mesh_name = "_".join(parts)

            cmds.blendShape(blendshape, edit=True, t=(neutral, 1, shape, 1.0))
            cmds.setAttr("{0}.{1}".format(blendshape, shape), 1)
            cmds.duplicate(neutral, name=split_mesh_name)

            self.cleanup_intermediate_shapes(split_mesh_name)

            split_meshes.append(split_mesh_name)
            cmds.blendShape(blendshape, edit=True, rm=True, t=(neutral, 1, shape, 1.0))

        return split_meshes

    def cleanup(self):
        # type: () -> None
        for _, (mesh, _) in self._mask_data.items():
            cmds.delete(mesh)
        self.masks = []
        self._mask_data = {}

    def cleanup_intermediate_shapes(self, transform):
        # type: (str) -> None
        """Delete any intermediate shape the given transform might have."""
        shapes = cmds.listRelatives(transform, s=1, fullPath=True)
        if len(shapes) > 1:
            for shape in shapes:
                if cmds.getAttr(shape + ".intermediateObject"):
                    connections = cmds.listConnections(shape)
                    if not connections:
                        cmds.delete(shape)
