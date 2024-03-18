import maya.OpenMaya as om
from maya import cmds
from dataclasses import dataclass
from typing import List, Tuple, Dict, Union, Any
import json
from rigging_toolkit.core.filesystem import Path

@dataclass
class NodeData:
    name: str
    node_type: str
    attributes: Dict[str, Tuple[str, Any]]  # Key-value pairs where keys are attribute names and values are tuples of their type and value.
    connections: List[Tuple[str, str]]
    
def serialize_attribute(attr_type, value):
    # type: (str, Any) -> Any
    if attr_type in ["double3", "float3"]:
        return list(value)
    elif attr_type == "matrix":
        return [list(row) for row in value]
    else:
        return value

def deserialize_attribute(attr_type, serialized_value):
    # type: (str, Any) -> Any
    if attr_type in ["double3", "float3"]:
        try:
            serialized_value = tuple(serialized_value[0])
        except:
            serialized_value = serialized_value
    elif attr_type == "matrix":
        serialized_value =  [tuple(row) for row in serialized_value[0]]
    else:
        serialized_value = serialized_value
        
    return serialized_value
    

def capture_openmaya_tree(start_node_name):
    # type: (str) -> Tuple[List[Any], List[Any]]
    sel_list = om.MSelectionList()
    sel_list.add(start_node_name)
    start_node = om.MObject()
    sel_list.getDependNode(0, start_node)

    visited_nodes = []
    visited_connections = []  # To avoid re-traversing the same connection.

    def traverse(current_node, direction):
        current_node_name = om.MFnDependencyNode(current_node).name()
        visited_nodes.append(current_node_name)

        dg_it = om.MItDependencyGraph(current_node, om.MItDependencyGraph.kNodeLevel, direction)

        while not dg_it.isDone():
            next_node = dg_it.currentItem()
            next_node_name = om.MFnDependencyNode(next_node).name()

            connection_str = (current_node_name, next_node_name) if direction == om.MItDependencyGraph.kDownstream else (next_node_name, current_node_name)
            
            if connection_str not in visited_connections:
                visited_connections.append(connection_str)
                traverse(next_node, direction)
            
            dg_it.next()

    traverse(start_node, om.MItDependencyGraph.kDownstream)
    traverse(start_node, om.MItDependencyGraph.kUpstream)

    return visited_nodes, visited_connections

def get_connected_attributes(connections):
    # type: (List[Any]) -> List[Any]
    attribute_connections = []
    
    for nodeA, nodeB in connections:
        # Get all the connections between nodeA and nodeB
        interconnections = cmds.listConnections(nodeA, destination=True, source=False, plugs=True) or []
        
        for interconnection in interconnections:
            # Check if the destination of the interconnection is in nodeB
            dest_node = interconnection.split('.')[0]
            if dest_node == nodeB:
                src_attr = cmds.listConnections(interconnection, source=True, destination=False, plugs=True)[0]
                dest_attr = interconnection
                conn = (src_attr, dest_attr)
                attribute_connections.append(conn)
                
    return attribute_connections
    
def capture_node_tree(node):
    # type: (str) -> List[NodeData]
    nodes, connection_nodes = capture_openmaya_tree(node)
    attribute_connections = get_connected_attributes(connection_nodes)

    # Create a list of NodeData instances
    node_data_list = []
    for n in nodes:
        node_attrs = cmds.listAttr(n, hd=True) or []
        custom_attrs = cmds.listAttr(n, ud=True) or []
        node_attr_values = {}
        for attr in node_attrs:
            is_custom = False
            exists = cmds.attributeQuery(attr,n=f"{n}", ex=True)
            if not exists:
                continue
            if not cmds.getAttr(f"{n}.{attr}", se=True):
                continue
            attr_type = cmds.getAttr(f"{n}.{attr}", typ=True)
            try:
                value = cmds.getAttr(f"{n}.{attr}")
            except:
                value = cmds.getAttr(f"{n}.{attr}", mi=True)
            if attr in custom_attrs:
                is_custom = True
            serialized_value = serialize_attribute(attr_type, value)
            node_attr_values[attr] = (attr_type, serialized_value, is_custom)

        node_type = cmds.nodeType(n)
        node_data = NodeData(name=n, node_type=node_type, attributes=node_attr_values, connections=[])
        node_data_list.append(node_data)

    # Add the connections to the NodeData instances
    for src, dest in attribute_connections:
        src_node = src.split('.')[0]
        dest_node = dest.split('.')[0]
        
        for nd in node_data_list:
            if nd.name == src_node:
                nd.connections.append((src, dest))
                

    return node_data_list
    
def serialize_node_data_to_json(node_data_list):
    # type: (List[NodeData]) -> str

    # Convert each NodeData instance to its dictionary representation
    serialized_list = [data.__dict__ for data in node_data_list]

    return json.dumps(serialized_list, indent=4)
    
def export_node_data_to_file(node_data_list, file_path):
    # type: (List[NodeData], Path) -> None
    json_data = serialize_node_data_to_json(node_data_list)

    with open(str(file_path), 'w') as file:
        file.write(json_data)
        
def deserialize_json_to_node_data(json_data):
    # type: (str) -> List[NodeData]
    data_list = json.loads(json_data)

    node_data_instances = []
    for data in data_list:
        attributes = data.get('attributes', {})
        deserialized_attributes = {}
        for attr, (attr_type, value) in attributes.items():
            deserialized_value = deserialize_attribute(attr_type, value)
            if isinstance(deserialized_value, list):
                deserialized_value = deserialized_value[0]
            deserialized_attributes[attr] = (attr_type, deserialized_value)

        # Override the original 'attributes' with the deserialized version
        data['attributes'] = deserialized_attributes

        # Convert the dictionary to a NodeData instance
        node_data_instances.append(NodeData(**data))

    return node_data_instances
    
def import_node_data_from_file(file_path):
    # type: (Path) -> List[NodeData]
    with open(str(file_path), 'r') as file:
        json_data = file.read()

    return deserialize_json_to_node_data(json_data)
    
def rebuild_node_network(node_data_list):
    # type: (List[NodeData]) -> None

    # Step 1: Create Nodes
    for node_data in node_data_list:
        if not cmds.objExists(node_data.name):
            cmds.createNode(node_data.node_type, name=node_data.name)

    # Step 2: Set Attributes
    for node_data in node_data_list:
        for attr, (attr_type, value) in node_data.attributes.items():
            if cmds.attributeQuery(attr, node=node_data.name, exists=True) and value is not None:
                deserialized_value = deserialize_attribute(attr_type, value)
                if cmds.attributeQuery(attr, node=node_data.name, i=True):
                    continue
                try:
                    if isinstance(deserialized_value, (list, tuple)) and not attr_type in ["string", "double3", "float3"]:
                        cmds.setAttr(f"{node_data.name}.{attr}", *deserialized_value)
                    elif attr_type == "string":
                        cmds.setAttr(f"{node_data.name}.{attr}", deserialized_value, type="string")
                    elif attr_type in ["double3", "float3"] and isinstance(deserialized_value, (list, tuple)):
                        cmds.setAttr(f"{node_data.name}.{attr}", deserialized_value[0], deserialized_value[1], deserialized_value[2])
                    else:
                        cmds.setAttr(f"{node_data.name}.{attr}", deserialized_value)
                except Exception as e:
                    print(f"Failed to set attribute: {node_data.name}.{attr} with value {deserialized_value}. Error: {e}")

    # Step 3: Establish Connections
    # This should be done last as we need to ensure the source and destination connections exist
    for node_data in node_data_list:
        for src, dest in node_data.connections:
            if cmds.objExists(src) and cmds.objExists(dest):
                if not cmds.isConnected(src, dest):
                    cmds.connectAttr(src, dest, f=True)


def export_node_network(node, file_path):
    # type: (str, Path) -> None
    node_data_list = capture_node_tree(node)
    export_node_data_to_file(node_data_list, file_path)

def import_node_network(file_path):
    # type: (Path) -> None
    node_data_list_from_file = import_node_data_from_file(file_path)
    rebuild_node_network(node_data_list_from_file)