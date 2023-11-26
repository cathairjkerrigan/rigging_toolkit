from maya import cmds
from pathlib import Path
import json
from typing import Optional, List
from rigging_toolkit.core.filesystem import find_new_version

def get_joint_data(selected_joints):
    # type: (List[str]) -> dict
    
    joint_data = []

    joint_data = []

    for joint in selected_joints:
        joint_info = {}
        
        # Name
        joint_info['name'] = cmds.ls(joint, shortNames=True)[0]
        
        # Position
        joint_info['position'] = cmds.xform(joint, query=True, worldSpace=True, translation=True)
        
        # Joint Orientation
        joint_info['jointOrient'] = cmds.getAttr(joint + ".jointOrient")[0]
        
        # Rotation
        joint_info['rotation'] = cmds.xform(joint, query=True, worldSpace=True, rotation=True)
        
        # Rotation Order
        joint_info['rotationOrder'] = cmds.xform(joint, query=True, worldSpace=True, rotateOrder=True)
                
        # Parent
        parents = cmds.listRelatives(joint, parent=True, fullPath=True)
        joint_info['parent'] = parents[0] if parents else None
        
        # Custom attributes
        attrs = cmds.listAttr(joint, userDefined=True)
        if attrs:
            joint_info['custom_attributes'] = {attr: cmds.getAttr(joint + "." + attr) for attr in attrs}
        else:
            joint_info['custom_attributes'] = {}
        
        joint_data.append(joint_info)

def export_rigging_template(name, path=None, joints=None):
    # type: (str, Optional[Path], Optional[List[str]]) -> None
    if path is None:
        path = Path(__file__).resolve().parent / "default_templates"

    if joints is None:
        joints = cmds.ls(sl=1, exactType="joint")

    if joints:
        data = get_joint_data(joints)

        new_version, _ = find_new_version(path, name, "json")

        with open(str(new_version), 'w') as f:
            json.dump(data, f, indent=4)


    

            