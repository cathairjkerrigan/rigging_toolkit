import maya.api.OpenMaya as om2
from maya import cmds
from typing import Optional, Union, List, Text
from .general import deformers_by_type
from pathlib import Path
from xml.etree import ElementTree

import logging

logger = logging.getLogger(__name__)

def get_skin_cluster(mesh):
    # type: (str) -> Optional[str]
    """Return the skincluster node attached to the mesh."""

    skin_cluster_list = deformers_by_type(mesh, "skinCluster")
    if skin_cluster_list:
        return skin_cluster_list[0]
    return None


def check_max_influences(max_influences=8):
    # type: (Optional[int]) -> list
    """
    Checks if any skinClusters in the scene violate the max influences and returns
    a list of meshes where Max Influences are greater than the passed max value.

    """

    cmds.select(clear=True)
    skin_clusters = cmds.ls(type="skinCluster")
    max_influences_violated_meshes = []
    for cluster in skin_clusters:
        cluster_geo = cmds.skinCluster(cluster, q=True, geometry=True)
        if cluster_geo:
            for mesh in cluster_geo:
                influences = num_influences(cluster, mesh, max_influences)
                if influences > max_influences:
                    max_influences_violated_meshes.append(mesh)
                    logger.warning(
                        "Mesh {0} has up to {1} influences per vertex, only {2} allowed.".format(
                            mesh,
                            influences,
                            max_influences,
                        )
                    )

    return max_influences_violated_meshes


def num_influences(cluster, mesh, show_above):
    # type: (str, str, int) -> int
    """
    Returns the max influence of the passed skinCluster per vertex.

    """
    vertices = cmds.polyListComponentConversion(mesh, toVertex=True)
    vertices = cmds.filterExpand(vertices, selectionMask=31)  # polygon vertex
    max_count = 0

    if vertices:
        for vert in vertices:
            joints = cmds.skinPercent(
                cluster, vert, query=True, ignoreBelow=0.00001, transform=None
            )

            count = len(joints)
            if count > max_count:
                max_count = count
            if count > show_above:
                logger.warning("mesh {0} vertex {1} has {2} influences per vertex.".format(mesh, vert, count))

    return max_count


def prune_influences(meshes, max_influence=8):
    # type: (list, Optional[int]) -> None
    """
    Prunes influences to match the provided max influence for each
    mesh in the provided list.

    """

    for mesh in meshes:
        skin = get_skin_cluster(mesh)
        verts = cmds.ls(mesh + ".vtx[*]", fl=True)

        for vtx in verts:
            weights = cmds.skinPercent(
                skin, vtx, ignoreBelow=0.00001, query=True, value=True
            )
            if weights is not None and len(weights) > max_influence:
                max_weights = [0.0] * len(weights)

                for weight in weights:
                    # Find the index where the current weight should be inserted
                    # in max_weights
                    j = len(weights) - 1
                    while j >= 0 and weight > max_weights[j]:
                        j -= 1
                    j += 1

                    for k in range(len(weights) - 1, j - 1, -1):
                        max_weights[k] = max_weights[k - 1]

                    max_weights[j] = weight

                prune_value = max_weights[max_influence] + 0.001
                logger.info(prune_value)

                cmds.skinPercent(skin, vtx, pruneWeights=prune_value)

def export_skin_weights(mesh, path):
    # type: (str, Union[str, Path]) -> Path
    weights_path = Path(path)
    logger.info(f"Exporting weights from {mesh} to {str(weights_path)}")

    skin_clusters = deformers_by_type(mesh, "skinCluster")
    if not skin_clusters:
        logger.warning(
            f"No skinCluster found on {mesh}, cannot export weights."
        )
        return
    
    weights_folder = str(weights_path.parent)

    cmds.deformerWeights(
        weights_path.name, path=weights_folder, ex=True, deformer=skin_clusters[0]
    )

def bind_skin(mesh, joints):
    # type: (Text, List[Text]) -> Text
    """Bind the mesh to the joints"""

    existing_joints = [j for j in joints if cmds.objExists(j)]

    missing_joints = list(set(existing_joints) - set(joints))
    if missing_joints:
        logger.warning(
            "These joints were not found in the scene and have not "
            f"been added to the skincluster: {missing_joints}"
        )

    skin_cluster = cmds.skinCluster(
        existing_joints,
        mesh,
        toSelectedBones=True,
        bindMethod=0,
        skinMethod=0,
        normalizeWeights=1,
    )  # type: List[Text]

    return skin_cluster[0]

def import_skin_weights(mesh, weights_path):
    # type: (str, Path) -> None
    """Import the maya skin weights on the mesh.

    This will automatically bind the mesh to the relevant joints if it has no skincluster.
    """

    logger.info(f"Importing maya weights for {mesh} from {weights_path}")

    weights_dir = str(weights_path.parent)
    weights_file = weights_path.name

    skin_cluster = get_skin_cluster(mesh)
    if not skin_cluster:
        joints = joints_from_weights(weights_path)
        skin_cluster = bind_skin(mesh, joints)

    cmds.deformerWeights(
        weights_file, im=True, method="index", deformer=skin_cluster, path=weights_dir
    )
    cmds.skinCluster(skin_cluster, edit=True, forceNormalizeWeights=True)

def joints_from_weights(weights_path):
    # type: (Path) -> List[str]
    """List the joints used in an maya skin weights file."""
    joints = []
    tree = ElementTree.parse(str(weights_path))
    root = tree.getroot()
    for element in root:
        joint = element.attrib.get("source")
        if joint:
            joints.append(joint)
    return joints

def transfer_skin_cluster(source_mesh, target_mesh):
    # type: (str, str) -> None
    """Transfer the skin weights from the source to the target.

    If the target mesh isn't bound, it will be bound to the joints deforming the source mesh.
    If the target mesh is missing some joints from the source mesh, they will automatically be added.
    """
    source_skin_cluster = get_skin_cluster(source_mesh)

    if not source_skin_cluster:
        raise RuntimeError("Source mesh has no skin cluster attached.")

    source_joints = cmds.skinCluster(source_skin_cluster, query=True, influence=True)

    target_skin_cluster = get_skin_cluster(target_mesh)

    if not target_skin_cluster:
        target_skin_cluster = bind_skin(target_mesh, source_joints)
    else:
        # make sure all the source joints are in the target skin cluster
        target_joints = cmds.skinCluster(
            target_skin_cluster, query=True, influence=True
        )
        for joint in source_joints:
            if joint not in target_joints:
                cmds.skinCluster(
                    target_skin_cluster, edit=True, addInfluence=joint, weight=0.0
                )

    cmds.copySkinWeights(
        sourceSkin=source_skin_cluster,
        destinationSkin=target_skin_cluster,
        noMirror=True,
        surfaceAssociation="closestPoint",
        influenceAssociation="closestJoint",
    )