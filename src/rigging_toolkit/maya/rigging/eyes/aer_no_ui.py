from maya import cmds, OpenMaya
from rigging_toolkit.maya.utils import exists, get_shapes
from typing import List, Optional, Tuple
import math
import logging
import re

logger = logging.getLogger(__name__)

class AER():
    '''Headless Rewrite of UKDP AER''' # print AER.__doc__
	
    def __init__ (self, rig_name, eye_locator, upper_lid_vertices, lower_lid_vertices, parent_jnt=None, parent_control=None, parent_grp=None):
        # type: (str, str, List[str], List[str], Optional[str], Optional[str], Optional[str]) -> None
        
        self.rig_name = rig_name
        self.eye_locator = eye_locator
        self.upper_lid_vertices = upper_lid_vertices
        self.lower_lid_vertices = lower_lid_vertices
        self.parent_jnt = parent_jnt
        self.parent_control = parent_control
        self.parent_grp = parent_grp

        self.main_grp = f"{rig_name}_GRP"
        self.main_ctrl_grp = "Eyelids_CTRL_GRP"

        self.upper_lid_joints = []
        self.lower_lid_joints = []
        self.upper_lid_locators = []
        self.lower_lid_locators = []

        self._validate()
        self.build()

    def _validate(self):
        # type: () -> None
        '''
        Validate that all of our required data exists within our Maya scene before
        starting the 
        '''
        if exists(self.rig_name):
            raise ValueError(f"Eye rig name {self.rig_name} already in use in scene.")
        
        if not exists(self.eye_locator):
            raise ValueError(f"Eye locator {self.eye_locator} doesn't exist.")
        
        missing_upper_verts = [x for x in self.upper_lid_vertices if not exists(x)]
        if missing_upper_verts:
            raise ValueError(f"Missing vertices from Upper Lid {missing_upper_verts}")
        
        missing_lower_verts = [x for x in self.lower_lid_vertices if not exists(x)]
        if missing_lower_verts:
            raise ValueError(f"Missing vertices from Upper Lid {missing_lower_verts}")
        
        if self.parent_jnt is not None and exists(self.parent_jnt) is False:
            raise ValueError(f"Parent joint {self.parent_jnt} doesn't exist.")
        
        if self.parent_control is not None and exists(self.parent_control) is False:
            raise ValueError(f"Parent control {self.parent_control} doesn't exist.")
	
    def build(self):
        # type: () -> None
        self.create_grps()
        self.create_joints()
        self.create_sets()
        self.create_eyelid_locs()
        self.create_eyelid_curves()
        self.connect_locators_to_curves()
        self.create_driver_curves()
        self.create_joint_controls()
        self.create_curve_controls()
        self.add_smart_blink()

    def create_grps(self):
        # type: () -> None
        if not exists(self.main_grp):
            self.main_grp = cmds.group(n=self.main_grp, em=True, w=True)

        if self.parent_grp and exists(self.parent_grp):
            cmds.parent(self.main_grp, self.parent_grp)
        elif self.parent_grp and not exists(self.parent_grp):
            self.parent_grp = cmds.group(n=self.parent_grp, em=True, w=True)
            cmds.parent(self.main_grp, self.parent_grp)

        self.parent_jnt_grp = cmds.group(n=f"{self.rig_name}_Eyelids_JNT_GRP", em=True, p=self.main_grp)
        cmds.setAttr(f"{self.parent_jnt_grp}.visibility", 0)
        self.upper_lid_jnt_grp = cmds.group(n=f"{self.rig_name}_Upper_Eyelids_JNT_GRP", em=True, p=self.parent_jnt_grp)
        self.lower_lid_jnt_grp = cmds.group(n=f"{self.rig_name}_Lower_Eyelids_JNT_GRP", em=True, p=self.parent_jnt_grp)

        self.parent_loc_grp = cmds.group(n=f"{self.rig_name}_Eyelids_LOC_GRP", em=True, p=self.main_grp)
        cmds.setAttr(f"{self.parent_loc_grp}.visibility", 0)
        self.upper_loc_grp = cmds.group(n=f"{self.rig_name}_Upper_Eyelids_LOC_GRP", em=True, p=self.parent_loc_grp)
        self.lower_loc_grp = cmds.group(n=f"{self.rig_name}_Lower_Eyelids_LOC_GRP", em=True, p=self.parent_loc_grp)

        self.parent_curve_grp = cmds.group(n=f"{self.rig_name}_Eyelids_Curve_GRP", em=True, p=self.main_grp)
        cmds.setAttr(f"{self.parent_curve_grp}.visibility", 0)
        self.upper_curve_grp = cmds.group(n=f"{self.rig_name}_Upper_Eyelids_Curve_GRP", em=True, p=self.parent_curve_grp)
        self.lower_curve_grp = cmds.group(n=f"{self.rig_name}_Lower_Eyelids_Curve_GRP", em=True, p=self.parent_curve_grp)

        self.controller_joints_grp = cmds.group(n=f"{self.rig_name}_Eyelids_CTRL_JNT_GRP", em=True, p=self.main_grp)

        if not exists(self.main_ctrl_grp) and exists(self.parent_control):
            self.main_ctrl_grp = cmds.group(n=self.main_ctrl_grp, em=1, p=self.parent_control)
        elif not exists(self.main_ctrl_grp) and not exists(self.parent_control):
            self.main_ctrl_grp = cmds.group(n=self.main_ctrl_grp, em=1, w=1)

        self.eyelids_ctrl_grp = cmds.group(n=f"{self.rig_name}_Eyelids_CTRL_GRP", em=1, p=self.main_ctrl_grp)

    def create_joints(self):
        # type: () -> None
        cmds.select(clear=True)

        # remove any common vertices
        self.lower_lid_vertices = [x for x in self.lower_lid_vertices if x not in self.upper_lid_vertices]

        upper_joints, upper_center_joints = self.create_jnt_per_vertex(self.upper_lid_vertices, "Upper")
        self.upper_lid_joints.extend(upper_joints)
        cmds.parent(upper_center_joints, self.upper_lid_jnt_grp)

        lower_joints, lower_center_joints = self.create_jnt_per_vertex(self.lower_lid_vertices, "Lower")
        self.lower_lid_joints.extend(lower_joints)
        cmds.parent(lower_center_joints, self.lower_lid_jnt_grp)

    def create_jnt_per_vertex(self, vertices, eyelid):
        # type: (List[str], str) -> Tuple[List[str], List[str]]

        joints = []
        center_joints = []

        count = 1
        for vtx in vertices:
            cmds.select(clear=True)
            jnt = cmds.joint(rad=0.01, n=f"{self.rig_name}_{eyelid}_Eyelid_JNT{count}_SKIN")
            joints.append(jnt)
            pos = cmds.xform (vtx, q=1, ws=1, t=1)
            cmds.xform(jnt, ws=1, t=pos)
            center_pos = cmds.xform(self.eye_locator, q=1, ws=1, t=1)
            cmds.select(clear=True)
            center_jnt = cmds.joint(rad=0.01, n=f"{self.rig_name}_{eyelid}_Eyelid_JNT{count}_BASE")
            cmds.xform(center_jnt, ws=1, t=center_pos)
            cmds.parent(jnt, center_jnt)
            cmds.select(clear=True)
            cmds.joint(center_jnt, e=1, oj="xyz", secondaryAxisOrient="yup", ch=1, zso=1)
            center_joints.append(center_jnt)
            count += 1

        return joints, center_joints
    
    def create_sets(self):
        # type: () -> List[str]
        self.skin_joints = []
        self.skin_joints.extend(self.upper_lid_joints)
        self.skin_joints.extend(self.lower_lid_joints)

        set_skin_joints = cmds.sets(em=1, n=f"{self.rig_name}_joints_for_skin")
        for jnt in self.skin_joints:
            self.skin_set = cmds.sets(jnt, e=1, forceElement=set_skin_joints)

        return self.skin_joints

    def create_eyelid_locs(self):
        # type: () -> None
        upper_lid_locs = self.create_loc_per_joint(self.upper_lid_joints)
        self.upper_lid_locators.extend(upper_lid_locs)
        cmds.parent(upper_lid_locs, self.upper_loc_grp)

        lower_lid_locs = self.create_loc_per_joint(self.lower_lid_joints)
        self.lower_lid_locators.extend(lower_lid_locs)
        cmds.parent(lower_lid_locs, self.lower_loc_grp)

    def create_loc_per_joint(self, joints):
        # type: (List[str]) -> List[str]
        locators = []
        for jnt in joints:
            name = jnt.replace("_SKIN", "_loc")
            loc = cmds.spaceLocator(n=name)[0]
            cmds.setAttr (f"{loc}Shape.localScaleX", 0.025)
            cmds.setAttr (f"{loc}Shape.localScaleY", 0.025)
            cmds.setAttr (f"{loc}Shape.localScaleZ", 0.025)
            jnt_pos = cmds.xform(jnt, q=1, ws=1, t=1)
            cmds.xform(loc, ws=1, t=jnt_pos)
            jnt_parent = cmds.listRelatives(jnt, p=1)[0]
            cmds.aimConstraint(loc, jnt_parent, w=1, aimVector=(1,0,0), upVector=(0,1,0), worldUpType="vector", worldUpVector=(0,1,0))
            locators.append(loc)
        return locators
    
    def create_eyelid_curves(self):
        # type: () -> None
        self.upper_lid_base_curve = self.create_curve_from_vertices(self.upper_lid_vertices, "Upper")
        cmds.parent(self.upper_lid_base_curve, self.upper_curve_grp)
        
        self.lower_lid_base_curve = self.create_curve_from_vertices(self.lower_lid_vertices, "Lower")
        cmds.parent(self.lower_lid_base_curve, self.lower_curve_grp)

    def create_curve_from_vertices(self, vertices, eyelid):
        # type: (List[str], str) -> str
        edges = cmds.polyListComponentConversion(vertices, fv=1, te=1, internal=1)
        # polyToCurve works properly from selection rather than passing the selection list
        # so we need to overwrite any current selection with our edges and call the command
        cmds.select(edges, r=True)
        temp_curve = cmds.polyToCurve(form = 0, degree = 1)[0]
        cmds.delete(temp_curve, ch=True)
        name = f"{self.rig_name}_{eyelid}_Eyelid_BASE_Curve"
        new_curve = cmds.rename(temp_curve, name)
        return new_curve
    
    def connect_locators_to_curves(self):
        # type: () -> None
        self.connect_locators_to_curve(self.upper_lid_locators, self.upper_lid_base_curve)
        self.connect_locators_to_curve(self.lower_lid_locators, self.lower_lid_base_curve)

    def connect_locators_to_curve(self, locators, curve):
        # type: (List[str], str) -> None

        for loc in locators:
            pos = cmds.xform(loc, q=1, ws=1, t=1)
            u = self.getUParam(pos, curve)
            name = loc.replace("_loc", "_point_on_curve_info")
            curve_point_node = cmds.createNode("pointOnCurveInfo", n=name)
            cmds.connectAttr(f"{curve}.worldSpace", f"{curve_point_node}.inputCurve")
            cmds.setAttr(f"{curve_point_node}.parameter", u)
            cmds.connectAttr(f"{curve_point_node}.position", f"{loc}.t")

    def getUParam (self, pnt = [], crv = None, *args):
        '''MARCO GIORDANO'S CODE (http://www.marcogiordanotd.com/)'''

        point = OpenMaya.MPoint(pnt[0],pnt[1],pnt[2])
        curveFn = OpenMaya.MFnNurbsCurve(self.getDagPath(crv))
        paramUtill=OpenMaya.MScriptUtil()
        paramPtr=paramUtill.asDoublePtr()
        isOnCurve = curveFn.isPointOnCurve(point)
        if isOnCurve == True:
            curveFn.getParamAtPoint(point , paramPtr,0.001,OpenMaya.MSpace.kObject )
        else :
            point = curveFn.closestPoint(point,paramPtr,0.001,OpenMaya.MSpace.kObject)
            curveFn.getParamAtPoint(point , paramPtr,0.001,OpenMaya.MSpace.kObject )

        param = paramUtill.getDouble(paramPtr)  
        return param
    
    def getDagPath (self, objectName):
        '''MARCO GIORDANO'S CODE (http://www.marcogiordanotd.com/)'''

        if isinstance(objectName, list)==True:
            oNodeList=[]
            for o in objectName:
                selectionList = OpenMaya.MSelectionList()
                selectionList.add(o)
                oNode = OpenMaya.MDagPath()
                selectionList.getDagPath(0, oNode)
                oNodeList.append(oNode)
            return oNodeList
        else:
            selectionList = OpenMaya.MSelectionList()
            selectionList.add(objectName)
            oNode = OpenMaya.MDagPath()
            selectionList.getDagPath(0, oNode)
            return oNode
        
    def create_driver_curves(self):
        # type: () -> None
        upper_lid_eps = self.get_curve_EPs(self.upper_lid_base_curve)
        lower_lid_eps = self.get_curve_EPs(self.lower_lid_base_curve)
        upper_lid_guide_curve = self.create_guide_curve(upper_lid_eps)
        lower_lid_guide_curve = self.create_guide_curve(lower_lid_eps)
        self.corner_A_pos, self.corner_B_pos = self.get_eyelid_corner_pos(upper_lid_eps, upper_lid_guide_curve, lower_lid_eps, lower_lid_guide_curve)
        upper_cv_pos = self.get_pos_from_curve_cvs(upper_lid_guide_curve)
        lower_cv_pos = self.get_pos_from_curve_cvs(lower_lid_guide_curve)
        upper_cvs_ordered, lower_cvs_ordered = self.order_cvs(self.corner_A_pos, self.corner_B_pos, upper_cv_pos, lower_cv_pos)
        self.upper_lid_driver_curve = self.create_driver_curve(upper_cvs_ordered, self.upper_lid_base_curve, self.upper_curve_grp)
        self.lower_lid_driver_curve = self.create_driver_curve(lower_cvs_ordered, self.lower_lid_base_curve, self.lower_curve_grp)
        cmds.delete([upper_lid_guide_curve, lower_lid_guide_curve])
        cmds.select(cl=1)
        wire_node_up_lid_name = self.upper_lid_base_curve.replace("_BASE_Curve", "_control_curve_wire")
        wire_up_lid = cmds.wire(self.upper_lid_base_curve, n=wire_node_up_lid_name, w=self.upper_lid_driver_curve, gw = 0, en = 1, ce = 0, li = 0)
        wire_node_low_lid_name = self.lower_lid_base_curve.replace("_BASE_Curve", "_control_curve_wire")
        wire_low_lid = cmds.wire(self.lower_lid_base_curve, n=wire_node_low_lid_name, w=self.lower_lid_driver_curve, gw = 0, en = 1, ce = 0, li = 0)

    def get_curve_EPs(self, curve):
        # type: (str) -> List[List[float]]
        
        temp_curve = cmds.duplicate(curve)[0]
        cmds.delete(temp_curve, ch=1)
        cmds.rebuildCurve(temp_curve, rpo=1, end=1, kr=2, kcp=0, kep=1, kt=0, s=4, d=7, tol=0.01)

        temp_EPs_positions = []

        curve_eps = cmds.ls(f"{temp_curve}.ep[*]", fl=True)

        for ep in curve_eps:
            ep_pos = cmds.xform(ep, q=1, ws=1, t=1)
            temp_EPs_positions.append(ep_pos)

        cmds.delete(temp_curve)
        return temp_EPs_positions

    def create_guide_curve(self, ep_positions):
        # type: (List[str]) -> str
        guide_curve = cmds.curve(d=3, ep=(ep_positions[0], ep_positions[1], ep_positions[2], ep_positions[3], ep_positions[4]))
        return guide_curve

    def get_eyelid_corner_pos(self, upper_ep_positions, upper_curve, lower_ep_positions, lower_curve):
        # type: (List[List[float]], str, List[List[float]], str) -> Tuple[List[float], List[float]]

        upper_corner_1 = upper_ep_positions[0]
        lower_corner_1 = lower_ep_positions[0]
        lower_corner_2 = lower_ep_positions[4]

        # distance formula is: d = sqrt((Ax-Bx)**2 + (Ay-By)**2 + (Az-Bz)**2)
        temp_distance_1 = math.sqrt((upper_corner_1[0] - lower_corner_1[0])**2 + (upper_corner_1[1] - lower_corner_1[1])**2 + (upper_corner_1[2] - lower_corner_1[2])**2)
        temp_distance_2 = math.sqrt((upper_corner_1[0] - lower_corner_2[0])**2 + (upper_corner_1[1] - lower_corner_2[1])**2 + (upper_corner_1[2] - lower_corner_2[2])**2)

        if temp_distance_1 > temp_distance_2:
            corner_EPs = [0, 4, 4, 0]
        else:
            corner_EPs = [0, 0, 4, 4]
        
        corner_A_pos = self.get_corner_pos(f"{upper_curve}.ep[{corner_EPs[0]}]", f"{upper_curve}.ep[{corner_EPs[1]}]")
        corner_B_pos = self.get_corner_pos(f"{upper_curve}.ep[{corner_EPs[2]}]", f"{upper_curve}.ep[{corner_EPs[3]}]")

        return (corner_A_pos, corner_B_pos)

    def get_corner_pos(self, upper_EP, lower_EP):
        # type: (str, str) -> List[float]

        temp_cluster = cmds.cluster(upper_EP, lower_EP, en=1)[1]
        temp_loc = cmds.spaceLocator()[0]
        cmds.pointConstraint(temp_cluster, temp_loc, mo=0, w=1)
        corner_pos = cmds.xform(temp_loc, q=1, ws=1, t=1)
        cmds.delete([temp_cluster, temp_loc])
        return corner_pos
    
    def get_pos_from_curve_cvs(self, curve):
        # type: (str) -> List[List[float]]
        curve_cvs_pos = []
        cvs = cmds.ls(f"{curve}.cv[*]", flatten=True)
        for cv in cvs:
            cv_pos = cmds.xform(cv, q=1, ws=1, t=1)
            print(f"cv pos {cv_pos}")
            curve_cvs_pos.append(cv_pos)

        return curve_cvs_pos
    
    def order_cvs(self, corner_A_pos, corner_B_pos, upper_cv_pos, lower_cv_pos):
        # type: (List[float], List[float], List[List[float]], List[List[float]]) -> Tuple(List[List[float]], List[List[float]])
        '''
        Order of CVs in base lists:			Order of CVs in ordered lists:
        (upper_cv_pos, lower_cv_pos)			(upper_cvs_ordered, lower_cvs_ordered)
        -----------------------				-------------------------
        INDEX | 		CV		|				| INDEX | 		CV		|
        ------|---------------|				|-------|---------------|
        	0	| corner: ?		|				|	0	| corner A		|
        	1	| 				|				|	1	| 				|
        	2	| 				|				|	2	| 				|
        	3	| middle of crv |				|	3	| middle of crv	|
        	4	| 				|				|	4	| 				|
        	5	| 				|				|	5	| 				|
        	6	| other corner  |				|	6	| corner B		|
        -----------------------				-------------------------

        - measure dist between first_CV of baseList and corner_A_pos
        - measure dist between first_CV of baseList and corner_B_pos
        - if CV is closer to cornerA append baseList to orderedList from beginning to end
        - else (CV closer to cornerB) append baseList to orderedList from end to beginning
        return orderedLists
        '''

        print(f"corner_A_pos = {corner_A_pos}")
        print(f"upper cv pos = {upper_cv_pos}")

        # distance formula is: d = sqrt((Ax-Bx)**2 + (Ay-By)**2 + (Az-Bz)**2)
        distTEMP1 = math.sqrt ((((upper_cv_pos[0])[0]) - corner_A_pos[0])**2 + (((upper_cv_pos[0])[1]) - corner_A_pos[1])**2 + (((upper_cv_pos[0])[2]) - corner_A_pos[2])**2)
        distTEMP2 = math.sqrt ((((upper_cv_pos [0])[0]) - corner_B_pos[0])**2 + (((upper_cv_pos[0])[1]) - corner_B_pos[1])**2 + (((upper_cv_pos[0])[2]) - corner_B_pos[2])**2)
        if distTEMP1 < distTEMP2 :
            upper_cvs_ordered = upper_cv_pos
        else:
            upper_cvs_ordered = upper_cv_pos[::-1] # reversed 'upper_cv_pos'

        distTEMP3 = math.sqrt ((((lower_cv_pos[0])[0]) - corner_A_pos[0])**2 + (((lower_cv_pos [0])[1]) - corner_A_pos[1])**2 + (((lower_cv_pos[0])[2]) - corner_A_pos[2])**2)
        distTEMP4 = math.sqrt ((((lower_cv_pos[0])[0]) - corner_B_pos[0])**2 + (((lower_cv_pos [0])[1]) - corner_B_pos[1])**2 + (((lower_cv_pos[0])[2]) - corner_B_pos[2])**2)
        if distTEMP3 < distTEMP4 :
            lower_cvs_ordered = lower_cv_pos
        else:
            lower_cvs_ordered = lower_cv_pos[::-1] # reversed 'lower_cv_pos'
            
        return upper_cvs_ordered, lower_cvs_ordered
    
    def create_driver_curve(self, ordered_cvs, base_curve, parent_grp):
        # type: (List[List[float]], str, str) -> str
        print(ordered_cvs)
        curve = cmds.curve(d=3, p=(ordered_cvs[0], ordered_cvs[1], ordered_cvs[2], ordered_cvs[3], ordered_cvs[4], ordered_cvs[5], ordered_cvs[6]))
        name = base_curve.replace("_BASE_", "_DRIVER_")
        renamed_curve = cmds.rename(curve, name)
        cmds.parent(renamed_curve, parent_grp)
        return renamed_curve
    
    def create_joint_controls(self):
        # type: () -> None
        self.control_joints = []
        upper_lid_driver_ep_pos = self.get_pos_from_curve_eps(self.upper_lid_driver_curve)
        lower_lid_driver_ep_pos = self.get_pos_from_curve_eps(self.lower_lid_driver_curve)
        upper_ctrl_joints = self.create_controller_joints(self.upper_lid_driver_curve, upper_lid_driver_ep_pos, "Upper_Eyelid")
        lower_ctrl_joints = self.create_controller_joints(self.lower_lid_driver_curve, lower_lid_driver_ep_pos, "Lower_Eyelid")
        self.control_joints.extend([x for x in upper_ctrl_joints if x not in self.control_joints])
        self.control_joints.extend([x for x in lower_ctrl_joints if x not in self.control_joints])

    def get_pos_from_curve_eps(self, curve):
        # type: (str) -> List[List[float]]
        curve_eps_pos = []
        EPs = cmds.ls(f"{curve}.ep[*]", flatten=True)
        for ep in EPs:
            cv_pos = cmds.xform(ep, q=1, ws=1, t=1)
            curve_eps_pos.append(cv_pos)

        return curve_eps_pos
    
    def create_controller_joints(self, skin_curve, ep_pos, jnt_name):
        # type: (str, List[List[float]], str) -> List[str]
        corner_A_jnt_ctrl = f"{self.rig_name}_Corner_A_CTRL_JNT"
        corner_B_jnt_ctrl = f"{self.rig_name}_Corner_B_CTRL_JNT"
        if not exists(corner_A_jnt_ctrl):
            corner_A_jnt_ctrl = cmds.joint(rad=0.05, p=self.corner_A_pos, n=f"{self.rig_name}_Corner_A_CTRL_JNT")
        if not exists(corner_B_jnt_ctrl):
            corner_B_jnt_ctrl = cmds.joint(rad=0.05, p=self.corner_B_pos, n=f"{self.rig_name}_Corner_B_CTRL_JNT")
        main_jnt_ctrl = cmds.joint(rad=0.05, p=ep_pos[2], n=f"{self.rig_name}_{jnt_name}_Main_CTRL_JNT")
        side_A_jnt_ctrl = cmds.joint(rad=0.05, p=ep_pos[1], n=f"{self.rig_name}_{jnt_name}_Secondary_A_CTRL_JNT")
        side_B_jnt_ctrl = cmds.joint(rad=0.05, p=ep_pos[3], n=f"{self.rig_name}_{jnt_name}_Secondary_B_CTRL_JNT")

        ctrl_jnts = [corner_A_jnt_ctrl, corner_B_jnt_ctrl, main_jnt_ctrl, side_A_jnt_ctrl, side_B_jnt_ctrl]

        for jnt in ctrl_jnts:
            if cmds.listRelatives(jnt, p=True) and cmds.listRelatives(jnt, p=True)[0] == self.controller_joints_grp:
                continue
            cmds.parent(jnt, self.controller_joints_grp)

        cmds.skinCluster(ctrl_jnts, skin_curve, n=f"{skin_curve}_skinCluster")

        return ctrl_jnts
    
    def create_curve_controls(self):
        # type: () -> None
        template_ctrl = self.create_template_controller()
        self.rig_controls = []
        ctrl_offsets = []

        for jnt in self.control_joints:
            ctrl_name = jnt.replace("_JNT", "")
            ctrl = cmds.duplicate(template_ctrl, n=ctrl_name)[0]
            self.rig_controls.append(ctrl)
            cmds.delete(cmds.pointConstraint(jnt, ctrl))
            orig_name = f"ORIG_{ctrl_name}"
            orig_grp = cmds.group(n=orig_name, em=1)
            cmds.delete(cmds.parentConstraint(ctrl, orig_grp))
            if "_Secondary" in ctrl:
                offset_grp_name = orig_name.replace("ORIG_", "OFFSET_")
                offset_grp = cmds.duplicate(orig_grp, n=offset_grp_name)[0]
                cmds.parent(ctrl, offset_grp)
                cmds.parent(offset_grp, orig_grp)
                ctrl_offsets.append(offset_grp)
            else:
                cmds.parent(ctrl, orig_grp)

            cmds.parent(orig_grp, self.eyelids_ctrl_grp)
            cmds.parentConstraint(ctrl, jnt)

        cmds.delete(template_ctrl)
        cmds.select(cl=1)

        # bad design...
        for ctrl in self.rig_controls:
            if "Corner_A" in ctrl:
                self.parent_constrain_ctrl_to_offset_grps(ctrl, ctrl_offsets, "Secondary_A")
            elif "Corner_B" in ctrl:
                self.parent_constrain_ctrl_to_offset_grps(ctrl, ctrl_offsets, "Secondary_B")
            elif "Upper_Eyelid_Main" in ctrl:
                self.parent_constrain_ctrl_to_offset_grps(ctrl, ctrl_offsets, "Upper_Eyelid_Secondary")
            elif "Lower_Eyelid_Main" in ctrl:
                self.parent_constrain_ctrl_to_offset_grps(ctrl, ctrl_offsets, "Lower_Eyelid_Secondary")

        main_ctrls = [x for x in self.rig_controls if "_Main_" in x]
        upper_secondary_ctrls = [x for x in self.rig_controls if "Upper_Eyelid_Secondary" in x]
        lower_secondary_ctrls = [x for x in self.rig_controls if "Lower_Eyelid_Secondary" in x]
        for ctrl in main_ctrls:
            cmds.addAttr(ctrl, ln="SecondaryControls", at="bool", k=0)
            cmds.setAttr(f"{ctrl}.SecondaryControls", 1, channelBox = 1)
            if "Upper_Eyelid" in ctrl:
                self.connect_main_ctrl_to_secondary(ctrl, upper_secondary_ctrls)
            elif "Lower_Eyelid" in ctrl:
                self.connect_main_ctrl_to_secondary(ctrl, lower_secondary_ctrls)

        self.lock_and_hide_ctrls(self.rig_controls)

    def lock_and_hide_ctrls(self, ctrls):
        attrs = ["sx", "sy", "sz", "v"]
        for ctrl in ctrls:
            for attr in attrs:
                cmds.setAttr(f"{ctrl}.{attr}", lock=1, keyable=False, channelBox=0)

    def connect_main_ctrl_to_secondary(self, ctrl, secondary_controls):
        # type: (str, List[str]) -> None
        for control in secondary_controls:
            cmds.connectAttr(f"{ctrl}.SecondaryControls", f"{control}.visibility", f=1)

    def parent_constrain_ctrl_to_offset_grps(self, ctrl, ctrl_offsets, offset_type):
        # type: (str, List, str) -> None
        offset_grps = [x for x in ctrl_offsets if offset_type in x]
        for offset in offset_grps:
            cmds.parentConstraint(ctrl, offset, mo=1)

    def create_template_controller(self):
        # type: () -> str
        temp_ctrl1 = cmds.circle(r=0.15)[0]
        temp_ctrl2 = cmds.duplicate(temp_ctrl1)[0]
        cmds.setAttr(f"{temp_ctrl2}.rotateY", 90)
        temp_ctrl3 = cmds.duplicate(temp_ctrl2)[0]
        cmds.setAttr(f"{temp_ctrl3}.rotateX", 90)
        cmds.parent(temp_ctrl2, temp_ctrl3, temp_ctrl1)
        cmds.makeIdentity([temp_ctrl2, temp_ctrl3], apply=True, t=1, r=1, s=1, n=0, pn=1)
        temp_ctrl2_shape = get_shapes(temp_ctrl2)[0]
        temp_ctrl3_shape = get_shapes(temp_ctrl3)[0]
        cmds.parent([temp_ctrl2_shape, temp_ctrl3_shape], temp_ctrl1, r=True, s=True)
        cmds.delete(temp_ctrl2, temp_ctrl3)
        cmds.select(cl=1)
        return temp_ctrl1
    
    def add_smart_blink(self):
        # type: () -> None
        main_up_ctrl = [x for x in self.rig_controls if "Upper_Eyelid_Main" in x][0]
        main_lower_ctrl = [x for x in self.rig_controls if "Lower_Eyelid_Main" in x][0]

        self.check_curves(self.upper_lid_driver_curve, self.lower_lid_driver_curve)

        smart_blink_main_curve = cmds.duplicate(self.upper_lid_driver_curve, n=f"{self.rig_name}_Eyelids_Smart_Blink_Curve")[0]
        cmds.parent(smart_blink_main_curve, self.parent_curve_grp)
        smart_blink_main_blendshape = cmds.blendShape(self.upper_lid_driver_curve, self.lower_lid_driver_curve, smart_blink_main_curve, n=f"{self.rig_name}_Eyelids_Smart_Blink_BSN")[0]
        cmds.addAttr(main_up_ctrl, ln="SmartBlinkHeight", at="float", min=0, max=1, k=1)
        cmds.connectAttr(f"{main_up_ctrl}.SmartBlinkHeight", f"{smart_blink_main_blendshape}.{self.upper_lid_driver_curve}", f=1)
        smart_blink_reverse = cmds.shadingNode("reverse", asUtility=1, n=f"{self.rig_name}_Eyelids_smartBlink_reverse")
        cmds.connectAttr(f"{main_up_ctrl}.SmartBlinkHeight", f"{smart_blink_reverse}.inputX", f=1)
        cmds.connectAttr(f"{smart_blink_reverse}.outputX", f"{smart_blink_main_blendshape}.{self.lower_lid_driver_curve}")

        upper_lid_smart_blink_curve = cmds.duplicate(self.upper_lid_base_curve, n=f"{self.rig_name}_Upper_Eyelid_Smart_Blink_Curve")[0]
        lower_lid_smart_blink_curve = cmds.duplicate(self.lower_lid_base_curve, n=f"{self.rig_name}_Lower_Eyelid_Smart_Blink_Curve")[0]
        upper_lid_smart_blink_curve = self.check_curves(self.upper_lid_base_curve, upper_lid_smart_blink_curve)
        lower_lid_smart_blink_curve = self.check_curves(self.lower_lid_base_curve, lower_lid_smart_blink_curve)
        cmds.setAttr(f"{main_up_ctrl}.SmartBlinkHeight", 1)
        cmds.select(cl=1)
        upper_lid_wire = cmds.wire(upper_lid_smart_blink_curve, n=f"{self.rig_name}_Upper_Eyelid_Smart_Blink_Wire", w=smart_blink_main_curve, gw=0, en=1, ce=0, li=0)[0]
        cmds.setAttr(f"{upper_lid_wire}.scale[0]", 0)
        cmds.setAttr(f"{main_up_ctrl}.SmartBlinkHeight", 0)
        cmds.select(cl=1)
        lower_lid_wire = cmds.wire(lower_lid_smart_blink_curve, n=f"{self.rig_name}_Lower_Eyelid_Smart_Blink_Wire", w=smart_blink_main_curve, gw=0, en=1, ce=0, li=0)[0]
        cmds.setAttr(f"{lower_lid_wire}.scale[0]", 0)

        upper_lid_smart_blink_blendshape = cmds.blendShape(upper_lid_smart_blink_curve, self.upper_lid_base_curve, n=f"{self.rig_name}_Upper_Eyelid_Smart_Blink_BSN")[0]
        lower_lid_smart_blink_blendshape = cmds.blendShape(lower_lid_smart_blink_curve, self.lower_lid_base_curve, n=f"{self.rig_name}_Lower_Eyelid_Smart_Blink_BSN")[0]

        for i in [main_up_ctrl, main_lower_ctrl]:
            cmds.addAttr(i, ln="SmartBlink", at="float", min=0, max=1, k=1)

        cmds.connectAttr(f"{main_up_ctrl}.SmartBlink", f"{upper_lid_smart_blink_blendshape}.{upper_lid_smart_blink_curve}", f=1)
        cmds.connectAttr(f"{main_lower_ctrl}.SmartBlink", f"{lower_lid_smart_blink_blendshape}.{lower_lid_smart_blink_curve}", f=1)
        cmds.setAttr(f"{main_up_ctrl}.SmartBlinkHeight", 0.15)

        logger.info(f"upper_lid_base: {self.upper_lid_base_curve}")
        logger.info(f"upper_lid_smart_blink: {upper_lid_smart_blink_curve}")
        logger.info(f"lower_lid_base: {self.lower_lid_base_curve}")
        logger.info(f"lower_lid_smart_blink_curve: {lower_lid_smart_blink_curve}")

    def check_curves(self, curve_1, curve_2):
        # type: (str, str) -> str
        curve_1_end_cv = self.get_cv_order_by_x_pos(curve_1)[-1]
        curve_2_end_cv = self.get_cv_order_by_x_pos(curve_2)[-1]

        if curve_1_end_cv == curve_2_end_cv:
            return curve_2
        
        logger.warning(f"reversing curve {curve_2}")
        reversed_curve = cmds.reverseCurve(curve_2, rpo=True)[0]
        return reversed_curve

    def get_cv_order_by_x_pos(self, curve):
        # type: (str) -> List

        cv_dict = {}
        ordered_cv_list = []

        for cv in cmds.ls(f"{curve}.cv[*]", flatten=True):
            pos_x = cmds.xform(cv, q=1, ws=1, t=1)[0]
            match = re.findall(r"[0-9]+", cv)[0]
            cv_dict[match] = pos_x
            
        sorted_list = dict(sorted(cv_dict.items(), key=lambda item: item[1]))

        for key in sorted_list.keys():
            ordered_cv_list.append(key)

        return ordered_cv_list

    def cleanup(self):
        # type: () -> None
        cmds.delete(self.skin_set)
        