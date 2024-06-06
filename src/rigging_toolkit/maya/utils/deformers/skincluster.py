import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
from maya import cmds
from typing import Optional, Union, List, Text
from .general import deformers_by_type
from rigging_toolkit.core.filesystem import Path
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

class SkinWeightsSmoother:
    def __init__(self, selection, depth, favor_edge_weight=0.5, use_faces=False):
        self.selection = selection
        self.depth = depth
        self.favor_edge_weight = favor_edge_weight
        self.use_faces = use_faces
        self.skin_cluster = None
        self.vertices = set()
        self.edges = set()
        self.mesh = None

    def initialize(self):
        # Convert selection to MObject
        self.mesh = self.get_dag_path(self.selection[0])

        # Get the skin cluster
        self.skin_cluster = self.get_skin_cluster(self.mesh)

        # Get the vertices in the selection
        self.vertices = set(self.selection)

        # Identify edge vertices
        self.edges = self.find_edge_vertices()

    def get_dag_path(self, vertex):
        selection_list = om2.MSelectionList()
        selection_list.add(vertex)
        dag_path, component = selection_list.getComponent(0)
        return dag_path

    def get_skin_cluster(self, dagPath):
        iter = om2.MItDependencyGraph(dagPath.node(), om2.MFn.kSkinClusterFilter, om2.MItDependencyGraph.kUpstream)
        while not iter.isDone():
            skinClusterNode = iter.currentItem()
            if skinClusterNode.apiType() == om2.MFn.kSkinClusterFilter:
                return oma2.MFnSkinCluster(skinClusterNode)
            iter.next()
        return None

    def find_edge_vertices(self):
        edge_vertices = set()
        vertIter = om2.MItMeshVertex(self.mesh)
        while not vertIter.isDone():
            if vertIter.index() in self.vertices:
                connectedVertices = vertIter.getConnectedVertices()
                for i in range(len(connectedVertices)):
                    if connectedVertices[i] not in self.vertices:
                        edge_vertices.add(vertIter.index())
                        break
            vertIter.next()
        return edge_vertices

    def smooth_weights(self):
        vertex_weights = self.get_vertex_weights()
        new_weights = {v: vertex_weights[v] for v in self.vertices}

        for v in self.edges:
            self.smooth_vertex_weights(v, new_weights, self.depth, vertex_weights)
        
        self.set_vertex_weights(new_weights)

    def get_vertex_weights(self):
        # Retrieve current weights for all vertices
        weights = {}
        infCount = len(self.skin_cluster.influenceObjects())
        vertIter = om2.MItMeshVertex(self.mesh)
        while not vertIter.isDone():
            index = vertIter.index()
            weights[index] = self.skin_cluster.getWeights(self.mesh, vertIter.currentItem())[0]
            vertIter.next()
        return weights

    def smooth_vertex_weights(self, vertex, new_weights, depth, vertex_weights):
        queue = [(vertex, 0)]
        visited = set()
        
        while queue:
            v, d = queue.pop(0)
            if v in visited or d > depth:
                continue
            visited.add(v)
            
            connectedVertices = om2.MItMeshVertex(self.mesh).getConnectedVertices()
            
            for i in range(len(connectedVertices)):
                neighbor = connectedVertices[i]
                if neighbor in self.vertices or neighbor in visited:
                    continue
                
                t = d / depth
                new_weights[neighbor] = (1 - t) * vertex_weights[vertex] + t * vertex_weights[neighbor]
                
                queue.append((neighbor, d + 1))

    def set_vertex_weights(self, weights):
        # Set the new weights to the vertices
        infCount = len(self.skin_cluster.influenceObjects())
        vertIter = om2.MItMeshVertex(self.mesh)
        while not vertIter.isDone():
            index = vertIter.index()
            self.skin_cluster.setWeights(self.mesh, vertIter.currentItem(), om2.MIntArray(infCount, 1), weights[index], False)
            vertIter.next()