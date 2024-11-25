import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
from maya import cmds
from typing import Optional, Union, List, Text
from .general import deformers_by_type
from rigging_toolkit.core.filesystem import Path
from xml.etree import ElementTree
import numpy as np
from rigging_toolkit.maya.utils.mesh_utils import get_vertex_neighbours
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

    weights_dir = str(weights_path.parent) # folder directory
    weights_file = weights_path.name # file_name

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

def get_skin_weights(name):
    # type: (str) -> dict
    """
    Returns the weights and influences of a skin cluster as a dictionary.
    This function assumes the whole mesh is bound to the skinCluster.

    name (str): The name of the skinCluster node to query

    Returns (dict): {
        'influences': ['joint1', 'joint2'],
        'weights': [
            {
                0: 0.25,
                1: 0.75
            }
        ]
    }
    """
    # get the influence names as a list with cmds because its dramatically easier than with om2
    influences = cmds.skinCluster(name, q=True, influence=True)

    # get the weight list plug. This is an array with one plug per vert of the skinned mesh
    msel = om2.MSelectionList()
    msel.add(f"{name}.weightList")
    weight_list_p = msel.getPlug(0)
    num_points = weight_list_p.numElements()

    # this list will hold the weights. The index of each element corresponds to the
    # vert id on the mesh. The list is pre-populated because its faster than appending
    # on large meshes
    weights = [{}] * num_points

    # iterate over each vert weight
    for i in range(num_points):
        weight_list_element_p = weight_list_p.elementByPhysicalIndex(i)

        # each weight list element has a single child plug that is a sparse array
        # for the weights. The plug index corresponds to the index of the influence.
        weight_p = weight_list_element_p.child(0)

        # holds the weights for the current vert
        vert_weights = {}

        # get the influence indices used for this vert
        indices = weight_p.getExistingArrayAttributeIndices()
        for index in indices:
            weight_element_p = weight_p.elementByLogicalIndex(index)
            value = weight_element_p.asDouble()

            # index represents the index of the influence
            vert_weights[index] = value

        weights[i] = vert_weights

    return {"influences": influences, "weights": weights}


def set_skin_weights(name, weight_data):
    # type: (str, dict) -> None
    """
    Sets the weights on a skinCluster with the given weight data.
    Function assumes that the weight data matches the mesh connected
    to the skinCluster.

    Weight data must be in the following format
    {
        'influences': ['joint1', 'joint2'],
        'weights': [
            {
                0: 0.25,
                1: 0.75
            }
        ]
    }
    The key in each weight dictionary corresponds to the influence index
    from the 'influences' key

    name (str): The name of the skinCluster node to set
    weight_data (dict): The weight data to apply to the skinCluster
    """

    skin_influences = cmds.skinCluster(name, q=True, influence=True)

    # create a lookup table that maps the index of the skinClusters influence with the index of
    # the influences in the passed weight_data.This will be used to determine which weight plug
    # index to apply the weight_data to
    inf_table = {}
    for i, inf in enumerate(weight_data["influences"]):
        if inf not in skin_influences:
            raise RuntimeError(
                f"{name} has is missing influence {inf}, unable to set weights"
            )
        inf_table[i] = skin_influences.index(inf)

    # get the weight list plug. This is an array with one plug per vert of the skinned mesh
    msel = om2.MSelectionList()
    msel.add(f"{name}.weightList")
    weight_list_p = msel.getPlug(0)
    num_points = weight_list_p.numElements()

    # iterate over the weights
    for i, weights in enumerate(weight_data["weights"]):
        weight_list_element_p = weight_list_p.elementByPhysicalIndex(i)

        # get the weight plug from the weight list element
        weight_p = weight_list_element_p.child(0)

        # Before applying the new weights, any existing weights on the vert need to be removed.
        indices = weight_p.getExistingArrayAttributeIndices()
        for index in indices:
            weight_element_p = weight_p.elementByLogicalIndex(index)
            weight_element_p.setDouble(0)

        # apply the weights to the plugs
        for index, weight in weights.items():
            # get the plug using logical index because the index must correspond with the joints
            # index on the skinCluster.
            # The inf_table is used incase the influence order is different from the passed
            # weight data than the influence order on the skin_cluster
            weight_element_p = weight_p.elementByLogicalIndex(inf_table[index])

            weight_element_p.setDouble(weight)


class SmoothSkinWeights(object):

    def __init__(
        self,
        skinCluster,  # type: str
        vertices=None,  # type: Optional[List[str]]
        iterations=1,  # type:  Optional[int]
        depth=3,  # type:  Optional[int]
        use_faces=True,  # type:  Optional[bool]
        include_overlap=True,  # type: Optional[bool]
        distance_threshold=0.1,  # type: Optional[float]
        smooth_factor=0.5,  # type: Optional[float]
    ):

        self._skinCluster = skinCluster
        self._vertices = vertices or self._get_vertices_from_skincluster()
        self._iterations = iterations
        self._depth = depth
        self._use_faces = use_faces
        self._include_overlap = include_overlap
        self._distance_threshold = distance_threshold
        self._smooth_factor = smooth_factor

        self._initial_weights = get_skin_weights(self._skinCluster)
        self._new_weights = self._initial_weights

    @property
    def skinCluster(self):
        return self._skinCluster

    @skinCluster.setter
    def skinCluster(self, skin_cluster):
        self._skinCluster = skin_cluster

    @property
    def vertices(self):
        return self._vertices

    @vertices.setter
    def vertices(self, v_ids):
        self._vertices = v_ids or self._get_vertices_from_skincluster()

    @property
    def iterations(self):
        return self._iterations

    @iterations.setter
    def iterations(self, iterations):
        self._iterations = iterations

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, depth):
        self._depth = depth

    @property
    def use_faces(self):
        return self._use_faces

    @use_faces.setter
    def use_faces(self, use_faces):
        self._use_faces = use_faces

    @property
    def include_overlap(self):
        return self._include_overlap

    @include_overlap.setter
    def include_overlap(self, include_overlap):
        self._include_overlap = include_overlap

    @property
    def distance_threshold(self):
        return self._distance_threshold

    @distance_threshold.setter
    def distance_threshold(self, distance_threshold):
        self._distance_threshold = distance_threshold

    @property
    def smooth_factor(self):
        return self._smooth_factor

    @smooth_factor.setter
    def smooth_factor(self, smooth_factor):
        self._smooth_factor = smooth_factor

    @property
    def initial_weights(self):
        return self._initial_weights

    @initial_weights.setter
    def initial_weights(self, initial_weights):
        self._initial_weights = initial_weights

    @property
    def new_weights(self):
        return self._new_weights

    @new_weights.setter
    def new_weights(self, new_weights):
        self._new_weights = new_weights

    @classmethod
    def new(
        self,
        skinCluster,
        vertices=None,
        iterations=1,
        depth=3,
        use_faces=True,
        include_overlap=True,
        distance_threshold=0.1,
        smooth_factor=0.5,
    ):
        return SmoothSkinWeights(
            skinCluster=skinCluster,
            vertices=vertices,
            iterations=iterations,
            depth=depth,
            use_faces=use_faces,
            include_overlap=include_overlap,
            distance_threshold=distance_threshold,
            smooth_factor=smooth_factor,
        )

    def _get_vertices_from_skincluster(self):
        return cmds.ls(
            f"{cmds.listRelatives(cmds.skinCluster(self._skinCluster, q=True, g=True), p=True)[0]}.vtx[*]",
            fl=True,
        )

    def normalize_weights(self, weights):
        total_weight = np.sum(weights)
        normalized_weights = weights / total_weight
        return normalized_weights

    def smooth_weight(self, current_weight, neighbor_weights, smooth_factor):
        all_joints = set(current_weight.keys())
        for neighbor_weight in neighbor_weights:
            all_joints.update(neighbor_weight.keys())

        all_joints = sorted(all_joints)
        joint_index = {joint: idx for idx, joint in enumerate(all_joints)}

        current_weight_array = np.zeros(len(all_joints))
        for joint, weight in current_weight.items():
            current_weight_array[joint_index[joint]] = weight

        neighbor_weight_arrays = []
        for neighbor_weight in neighbor_weights:
            neighbor_weight_array = np.zeros(len(all_joints))
            for joint, weight in neighbor_weight.items():
                neighbor_weight_array[joint_index[joint]] = weight
            neighbor_weight_arrays.append(neighbor_weight_array)

        neighbor_weight_arrays = np.array(neighbor_weight_arrays)

        smoothed_weight_array = np.zeros(len(all_joints))

        smoothed_weight_array += (1 - smooth_factor) * np.sum(
            neighbor_weight_arrays, axis=0
        )

        smoothed_weight_array += smooth_factor * current_weight_array

        smoothed_weight_array = self.normalize_weights(smoothed_weight_array)

        smoothed_weight = {
            joint: smoothed_weight_array[idx] for joint, idx in joint_index.items()
        }

        return smoothed_weight

    def run(self):

        for i in range(self.iterations):
            for vtx in self._vertices:
                v_id, neighbour_vertices = get_vertex_neighbours(
                    [vtx],
                    depth=self.depth,
                    use_faces=self.use_faces,
                    include_overlap=self.include_overlap,
                    distance_threshold=self.distance_threshold,
                )
                current_weight = self._new_weights["weights"][v_id[0]]
                neighbour_weights = [
                    self._new_weights["weights"][x] for x in neighbour_vertices
                ]
                self._new_weights["weights"][v_id[0]] = self.smooth_weight(
                    current_weight, neighbour_weights, self.smooth_factor
                )

        set_skin_weights(self.skinCluster, self._new_weights)


def get_mesh_from_skincluster(skin_cluster):
    # type: (str) -> str

    shape = cmds.skinCluster(skin_cluster, q=True, g=True)[0]
    mesh = cmds.listRelatives(shape, p=True)[0]
    return mesh


def get_influenced_vertices_from_skincluster(
    skin_cluster, joint_list=[], weight_threshold=0.01
):
    # type: (str, Optional[List[str]], Optional[float]) -> None

    mesh = get_mesh_from_skincluster(skin_cluster)

    num_vertices = cmds.polyEvaluate(mesh, vertex=True)

    affected_vertices = []

    if not joint_list:
        joint_list = cmds.skinCluster(skin_cluster, q=True, inf=True)

    for joint in joint_list:

        for i in range(num_vertices):
            weight = cmds.skinPercent(
                skin_cluster, f"{mesh}.vtx[{i}]", transform=joint, query=True
            )

            if weight >= weight_threshold:
                affected_vertices.append(i)

    return affected_vertices
