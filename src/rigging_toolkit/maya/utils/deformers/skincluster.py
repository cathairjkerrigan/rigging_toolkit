import maya.api.OpenMaya as om2
from maya import cmds
from typing import Optional
from .general import deformers_by_type

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
