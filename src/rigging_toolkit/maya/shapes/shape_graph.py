from maya import cmds
import re
from collections import OrderedDict
from rigging_toolkit.core.context import Context
import logging
from rigging_toolkit.core.filesystem import find_latest
from rigging_toolkit.maya.utils import import_asset, add_blendshape_target, list_shapes, activate_blendshape_targets, reset_blendshape_targets, import_weight_map, delete_history, add_blendshape_targets
from itertools import combinations
from rigging_toolkit.maya.utils.delta import ExtractCorrectiveDelta
import json
import os

logger = logging.getLogger(__name__)

class ShapeGraph(object):

    def __init__(self, context):
        # type: (Context) -> None

        self.context = context
        self.shape_dic = { 
                        "base_shapes": {"": ""},
                        "combo_shapes": {"": ""}
                        }
        
        self.combo_shape_dic = { 
                        "corrective_shapes": {}
                        }
        
        self.missing_base_shapes = []
        self.missing_base_shapes_from_combos = []
        self.expression_component_list = [] 
        self.used_base_shapes = []
        self.used_combo_shapes = []
        self.neutral = None
        self.blendshape = None
        self.full_shapes_grp = None
        self._ignore_list = ["_archive"]
        self.full_shapes_grp = "full_shapes_grp"
        self.splitted_face_blendshapes_grp = cmds.group(n='splitted_face_blendshapes', em=True, w=True)
        self.splitted_face_corrective_blendshapes_grp = cmds.group(n='splitted_face_corrective_blendshapes', em=True, w=True)
        cmds.parent(self.splitted_face_corrective_blendshapes_grp, self.splitted_face_blendshapes_grp)

        self.retrieve_shapes()
        # self.connect_expression()
        self.disable_viewport(disable_viewport=False)

    def retrieve_shapes(self):
        shapes_path = self.context.shapes_path
        for shape in shapes_path.iterdir():
            if shape.stem in self._ignore_list:
                continue
            shape = shape.stem.replace("_L1", "")
            self.analyse_shape(shape)

        # clean up of the empty key:value pair from initilisation
        self.shape_dic["base_shapes"].pop("")
        self.shape_dic["combo_shapes"].pop("")       
        self.shape_dic["base_shapes"] = OrderedDict(sorted(self.shape_dic["base_shapes"].items(), key=lambda t: t[0]))
        self.shape_dic["combo_shapes"] = OrderedDict(sorted(self.shape_dic["combo_shapes"].items(), key=lambda t: t[0]))       
        logger.info(self.shape_dic["base_shapes"])
        logger.info(self.shape_dic["combo_shapes"])

        self._evaluate_base_shapes()
        self._find_graph_children()

        self.neutral = self._load_neutral()

        self.load_shapes_from_shapes_folder()
        self.assign_splitting_groups()
        self.cleanup()

    def _evaluate_base_shapes(self):
        del self.missing_base_shapes[:]
        del self.missing_base_shapes_from_combos[:]
        
        for shape in self.shape_dic["combo_shapes"].values():
            # find all the components in the combo shapes
            
            # have to change regex to include lettes aswell          
            combo_component = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', shape)
            for component in combo_component:
                component = 'shp_{}'.format(component)
                if component in self.shape_dic["base_shapes"].values():
                    pass
                else:
                    self.missing_base_shapes.append(component)
                    self.missing_base_shapes_from_combos.append(shape) 

        if self.missing_base_shapes is not []:
            
            self.remove_duplicates_from_list(self.missing_base_shapes)
            logger.warning('the following base shapes: {} are used in combo shapes, but are missing in the shapes folder.'. format(self.missing_base_shapes))
            logger.warning('the following combo shapes: {} have missing components.'. format(self.missing_base_shapes_from_combos))

    def _find_graph_children(self):
        
        for shape in self.shape_dic["combo_shapes"].values():                         
            child_shape_components = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', shape)
            
            for component in child_shape_components:
                shp_component = 'shp_{}'.format(component)
                if shp_component in self.shape_dic["base_shapes"].values():
                    self.used_base_shapes.append(shp_component) 

            # find all the posible children to the active child components
            number_of_combinations = len(child_shape_components) -1
            if number_of_combinations <= 1:
                pass
            else:
                parent_shapes = [x for x in combinations(child_shape_components, number_of_combinations)]
                
                parent_shapes_list = []
                del parent_shapes_list[:]
                
                for index in range(2, number_of_combinations + 1):
                    parent_shapes = [x for x in combinations(child_shape_components, index)]
                    
                    parent_shapes_list.extend(parent_shapes)
                
                for i in parent_shapes_list:
                    parent_shape = self.convert_tuple_to_list(i)
                    parent_shape = '_'.join(parent_shape)
                    parent_shape = 'shp_{}'.format(parent_shape)
                    if parent_shape in self.shape_dic["combo_shapes"].values():
                        if parent_shape == shape:
                            pass
                        else:                   
                            self.used_combo_shapes.extend([parent_shape])
                                                                   
            if len(child_shape_components) is not len(self.used_base_shapes):
                del self.used_base_shapes[:]
                    
            if self.used_base_shapes is not []:
                corrective_list = self.used_base_shapes + self.used_combo_shapes
                self.combo_shape_dic["corrective_shapes"].update({shape:corrective_list})
            
            del self.used_base_shapes[:] 
            del self.used_combo_shapes[:]
        
        logger.info('Processing corrective shapes....')    
        logger.info(self.combo_shape_dic)
    
    def analyse_shape(self, shape):
        
        result = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', shape)
               
        if len(result) == 1:
            self.shape_dic["base_shapes"].update({"base_shape_{}".format(shape):shape})
                
        elif len(result) >= 1:                              
            self.shape_dic["combo_shapes"].update({"combo_shape_{}".format(shape):shape})

    def disable_viewport(self, disable_viewport=True):
        if disable_viewport:
            cmds.refresh(suspend=disable_viewport)
        else:
            cmds.refresh(suspend=disable_viewport)

    def remove_duplicates_from_list(self, list_to_check):
        return list(dict.fromkeys(list_to_check))
    
    def convert_tuple_to_list(self, tuple_to_convert):
        return list(tuple_to_convert)
    
    def _load_neutral(self):
        
        neutral_path = self.context.assets_path / "head" / "meshes"

        latest, _ = find_latest(neutral_path, "geo_head_L1", "abc")

        self.neutral = import_asset(latest)[0]

        return self.neutral

    def load_shapes_from_shapes_folder(self):
        cmds.select(cl=True)
        self.blendshape = cmds.blendShape(self.neutral, n="face_bs")[0]
        
        logger.info(f"self.blendshape = {self.blendshape}")
        
        self.full_shapes_grp = cmds.createNode("transform", n="full_shapes_grp")

        for _base_shp, shp in self.shape_dic["base_shapes"].items():
            
            latest_file, _ = find_latest(self.context.shapes_path / f"{shp}_L1", f"{shp}_L1", "abc")
            print(self.context.shapes_path / f"{shp}_L1")
            print(latest_file)
            asset = import_asset(latest_file)[0]
            print(asset)
            add_blendshape_target(blendshape=self.blendshape, target=asset)
            cmds.parent(f"{shp}_L1", self.full_shapes_grp)

        for _combo_shp, combo_shp in self.shape_dic["combo_shapes"].items():
            child_components = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', combo_shp)
            pattern = [c for c in child_components if 'shp_{}'.format(c) in self.missing_base_shapes]
            if pattern:
                pass
            else:
                latest_file, _ = find_latest(self.context.shapes_path / f"{combo_shp}_L1", f"{combo_shp}_L1", "abc")
                print(self.context.shapes_path / f"{combo_shp}_L1")
                asset = import_asset(latest_file)[0]
                cmds.parent(f"{combo_shp}_L1", self.full_shapes_grp)  

        sorted_combo_shapes_keys = sorted(self.shape_dic["combo_shapes"].values(), key=len)
        completed_correctives = []
        for combo_shp in sorted_combo_shapes_keys:
            if combo_shp in completed_correctives:
                continue
            completed_correctives.append(combo_shp)
            self.corrective_shape = self.calculate_delta(combo_shp)
            if self.corrective_shape is None:
                continue
            if isinstance(self.corrective_shape, list):
                add_blendshape_target(self.blendshape, self.corrective_shape[0])
            else:
                add_blendshape_target(self.blendshape, self.corrective_shape)
            
        # cmds.delete(self.full_shapes_grp)

    def calculate_delta(self, shape):
        sorted_correction_shapes_keys = sorted(self.combo_shape_dic["corrective_shapes"].keys(), key=len)       
        for key in sorted_correction_shapes_keys:        
            if key in self.combo_shape_dic["corrective_shapes"] and key == shape:
                
                logger.info(f'calculate delta for shape {key}')   
                logger.info(f'calculate using the shapes: {self.combo_shape_dic["corrective_shapes"][key]}') 
                neutral_calculate_delta = cmds.duplicate(self.neutral, name=f'neutral_calculate_{key}')[0]
                cmds.parent(neutral_calculate_delta, self.full_shapes_grp)
                print(key)
                
                self.delta_bs_name = cmds.blendShape(neutral_calculate_delta, n=f'bs_calculate_delta_{key}')[0]
                # add_blendshape_targets(self.delta_bs_name, "[f"{x}_L1" for x in self.combo_shape_dic["corrective_shapes"][key]]")
                add_blendshape_target(self.delta_bs_name, f"{key}_L1")

                target_shapes = self.combo_shape_dic["corrective_shapes"][key]

                if len(self.combo_shape_dic["corrective_shapes"][key]) == 2:
                    for corrective_shape in self.combo_shape_dic["corrective_shapes"][key]:
                        add_blendshape_target(self.delta_bs_name, f"{corrective_shape}_L1")
                        cmds.setAttr("{}.{}".format(self.delta_bs_name, f"{key}_L1"), 1)
                        cmds.setAttr("{}.{}".format(self.delta_bs_name, f"{corrective_shape}_L1"), -1)
                    self.corrective_shape = cmds.duplicate(neutral_calculate_delta, name= 'delta_{}_L1'.format(key))[0]
                    
                elif len(self.combo_shape_dic["corrective_shapes"][key]) > 2:

                    for corrective_shape in (self.combo_shape_dic["corrective_shapes"][key]):
                        component = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', corrective_shape)
                        if len(component) == 1:
                            # this handles all the core shapes
                            cmds.setAttr("{}.{}".format(self.delta_bs_name, f"{key}_L1"), 1)
                            add_blendshape_target(self.delta_bs_name, f"{corrective_shape}_L1")
                            cmds.setAttr("{}.{}".format(self.delta_bs_name, f"{corrective_shape}_L1"), -1)
                            
                        if len(component) >=2:
                            # this adds all the combo shapes
                            corrective_shape = 'delta_{}'.format(f"{corrective_shape}_L1")
                            add_blendshape_target(self.delta_bs_name, f"{corrective_shape}")
                            cmds.setAttr("{}.{}".format(self.delta_bs_name, f"{corrective_shape}"), -1)
                        else:
                            pass

                    self.corrective_shape = cmds.duplicate(neutral_calculate_delta, name= 'delta_{}_L1'.format(key))[0]

                # if target_shapes:
                #     print([f"{x}_L1" for x in self.combo_shape_dic["corrective_shapes"][key]])
                #     activate_blendshape_targets(self.delta_bs_name, [f"{x}_L1" for x in self.combo_shape_dic["corrective_shapes"][key]])

                #     self.corrective_shape = ExtractCorrectiveDelta.calculate(neutral_calculate_delta, f"{key}_L1")
                                            
                #     self.corrective_shape = cmds.duplicate(neutral_calculate_delta, name= 'delta_{}_L1'.format(key))[0]

                #     reset_blendshape_targets(self.delta_bs_name)

                else:
                    pass
            else:
                pass
        
        return self.corrective_shape
    
    def assign_splitting_groups(self):

        splitting_json, _ = find_latest(self.context.rigs_path / "data", "face_splitter", "json")
        with splitting_json.open() as f:
            data = json.load(f)

        shape_splitting_data = list(data.keys())[0]
        self.splitting_neutral = self.import_splitting_neutral()
        # self.split_bs_name = blendshape.create_blendshape(self.splitting_neutral, 'splitting_bs')
        self.split_blendshape = cmds.blendShape(self.splitting_neutral, n="splitting_bs")[0]
        # blendshape.add_blendshape_target(self.split_bs_name, self.splitting_neutral, self.neutral, index=0)
        add_blendshape_target(self.split_blendshape, self.neutral)
        cmds.blendShape(self.split_blendshape, edit=True, w=[(0, 1)])
        split_target = self.neutral.replace("|", "")
        cmds.setAttr(f"{self.split_blendshape}.{split_target}", 1)
        print(f"data = {data[shape_splitting_data]}")
        for i in data[shape_splitting_data]:
            splitting_group, split_values = next(iter(i.items()))
            print(splitting_group)
            print(self.shape_dic["base_shapes"].values())
            shapes = [x.replace("_L1", "") for x in i.get("shapes", [])]
            for shape in self.shape_dic["base_shapes"].values():
                if shape in shapes:
                    print("shape in shapes")
                    self.split_shape(shape, splitting_group)

    def import_splitting_neutral(self):
        latest_splitting_mesh, _ = find_latest(self.context.assets_path / "head" / "meshes", "geo_head_S1", "abc")
        if latest_splitting_mesh is None:
            latest_splitting_mesh, _ = find_latest(self.context.assets_path / "head" / "meshes", "geo_head_L1", "abc")

            splitting_mesh = import_asset(latest_splitting_mesh)[0]
            splitting_mesh = cmds.rename(splitting_mesh, "geo_head_S1")
            print(splitting_mesh)
            return splitting_mesh
        splitting_mesh = import_asset(latest_splitting_mesh)[0]
        return splitting_mesh
    
    def split_shape(self, shape, splitting_group):
        
        # splitting shapes
        facial_bs_targets = list_shapes(self.blendshape)
        match = [x for x in facial_bs_targets if x == f"{shape}_L1"]
        print("splitting_shape...")
        print(shape)
        print(splitting_group)
        print(match)
        corrective_matches = [x for x in facial_bs_targets if match[0].replace("shp_", "").replace("_L1", "") in x]
        print(match)
        print(corrective_matches)

        splitting_json, _ = find_latest(self.context.rigs_path / "data", "face_splitter", "json")
        with splitting_json.open() as f:
            data = json.load(f)

        mask_splitting_data = list(data.keys())[0]
        
        for corrective_match in corrective_matches:
            logger.info('process Shape_Splitting:__{}__'.format(corrective_match))

            for target in facial_bs_targets:
                cmds.setAttr('{}.{}'.format(self.blendshape, target), 0)
            # only activate the matching target    
            cmds.setAttr('{}.{}'.format(self.blendshape, corrective_match), 1)
            
            # issue two
            valid_splitting_groups = self.get_corrective_shape_splitting_group(corrective_match, splitting_group)
            logger.info('{} __splitted__ {}'.format( corrective_match, valid_splitting_groups))
            logger.info('starting:__...__')
            for i in data[mask_splitting_data]:
                splitting_group, masks = next(iter(i.items()))
                shapes = i.get("shapes", [])
                
                if not splitting_group == valid_splitting_groups:
                    print(f"Not this mask group {splitting_group}")
                    continue
                print(f"valid splitting groups: {valid_splitting_groups}\nsplitting group: {splitting_group}")
                if masks:
                    for mask in masks:
                        shp = f"{corrective_match}_x{mask}"
                        if cmds.objExists(shp):
                            continue
                        mask_path, _ = find_latest(self.context.utilities_path / "masks", f"msk_x{mask}", "wmap")
                        full_mask_path, _ = find_latest(self.context.utilities_path / "masks", "msk_xFull", "wmap")
                        import_weight_map(self.split_blendshape, self.neutral.replace("|", ""), mask_path)
                        logger.info('splitted {} from {}'.format(corrective_match,valid_splitting_groups))
                        logger.info('using the map {}'.format(mask_path))
                        # duplicate the splitted shape
                        cmds.setAttr(f'{self.splitting_neutral}.visibility', 0)
                        split_target = cmds.duplicate(self.splitting_neutral, n=shp)[0]
                        import_weight_map(self.split_blendshape, self.neutral.replace("|", ""), full_mask_path)
                        if 'delta_' in split_target:
                            cmds.parent(split_target, self.splitted_face_corrective_blendshapes_grp)
                            logger.info('finished splitting:__{}__'.format(split_target))
                            logger.info('__...__')
                        else:
                            cmds.parent(split_target, self.splitted_face_blendshapes_grp)
                            logger.info('finished splitting:__{}__'.format(split_target))
                            logger.info('__...__')
                elif splitting_group == "full_split" and not masks:
                    shp = f"{corrective_match}_xFullShape"
                    if cmds.objExists(shp):
                        continue
                    split_target = cmds.duplicate(self.splitting_neutral, n='{}_xFullShape'.format(corrective_match))[0]
                    if 'delta_' in split_target:
                            cmds.parent(split_target, self.splitted_face_corrective_blendshapes_grp)
                            logger.info('finished splitting:__{}__'.format(split_target))
                            logger.info('__...__')
                    else:
                        cmds.parent(split_target, self.splitted_face_blendshapes_grp)
                        logger.info('finished splitting:__{}__'.format(split_target))
                        logger.info('__...__')

            for target in facial_bs_targets:
                cmds.setAttr('{}.{}'.format(self.blendshape, target), 0)

    def get_corrective_shape_splitting_group(self, shape, splitting_group):
        
        corrective_components = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', shape.replace("shp_", "").replace("_L1", ""))
        
        if len(corrective_components) <= 1:
            return splitting_group
        
        else:            
            
            splitting_json, _ = find_latest(self.context.rigs_path / "data", "face_splitter", "json")
            with splitting_json.open() as f:
                data = json.load(f)
            
            shape_splitting_data = list(data.keys())[0]
            
            # finds all the shapes matching the same splitting group
            vertical_split = []
            horizontal_split = []
            four_split = []
            full_shapes = []

            print("corrective components...")
            print(corrective_components)

            for i in data[shape_splitting_data]:
                splitting_group, splits = next(iter(i.items()))
                print(splitting_group)
                shapes = i.get("shapes", [])
                print(shapes)
                print([x for x in corrective_components if f"shp_{x}_L1" in shapes])
                
                if splitting_group == "vertical_split":
                    vertical_split.extend([x for x in corrective_components if f"shp_{x}_L1" in shapes])
                    print(vertical_split)
                if splitting_group == "horizontal_split":
                    horizontal_split.extend([x for x in corrective_components if f"shp_{x}_L1" in shapes])
                    print(horizontal_split)
                if splitting_group == "four_split":
                    four_split.extend([x for x in corrective_components if f"shp_{x}_L1" in shapes])
                    print(four_split)

            print(vertical_split)
            print(horizontal_split)
            print(four_split)


            if vertical_split and any(x in vertical_split for x in corrective_components):
                return "vertical_split"
            elif four_split and any(x in four_split for x in corrective_components):
                return "four_split" 
            elif horizontal_split and any(x in horizontal_split for x in corrective_components):
                return "horizontal_split" 
            else:  
                return "full_split"
                # full_shapes.append(corrective_component)
           
            # # asigns the splitting group if the number of components matches the number of shapes in the vertical_split
            # if len(corrective_components) == len(vertical_split):
            #     return splitting_group
            
            # # asigns the splitting group if the number of components matches the number of shapes in the horizontal_split
            # if len(corrective_components) == len(horizontal_split):
            #     return splitting_group
            
            # # asigns the splitting group if the number of components matches the number of shapes in the horizontal_split and vertical_split
            # if len(horizontal_split) + len(vertical_split) == len(corrective_components):
            #     splitting_group = 'vertical_split'
            #     return splitting_group
            
            # # asigns the splitting group if the number of components matches the number of shapes in the full_shapes and vertical_split
            # if len(full_shapes) + len(vertical_split) == len(corrective_components):
            #     splitting_group = 'vertical_split'
            #     return splitting_group
            
            # # asigns the splitting group if the number of components matches the number of shapes in the four_split
            # elif len(four_split) >= 1:
            #     splitting_group = 'four_split'
            #     return splitting_group
            
            # else:
            #     return splitting_group
            
    def create_facial_bs_expression(self, bs_node, target):

        corrective_shp_components = re.findall(r'_(\d+|[A-Za-z]+(?:_[A-Za-z]+)*)', target)
        expression_driver_components = []
        splitting_type = target.split('_')[-1]
        for shape_split_type in self.expression_component_list:
            
            result = [x for x in shape_split_type for y in corrective_shp_components if y in x ]
            expression_driver_components.extend(result)

        expression_driver_components_side = []
        for component in expression_driver_components:

            component_side = component.split('_')[-1]

            if component_side == splitting_type:
                expression_driver_components_side.append(component)
            elif 'Center' in component:
                if "30L" in component:
                    if  "Left" in target and "30L" in target and "30R" not in target:
                        expression_driver_components_side.append(component)
                    elif "Right" in target and "30L" in target and "30R" not in target:
                        expression_driver_components_side.append(component)
                elif "30R" in component:
                    if  "Left" in target and "30R" in target and "30L" not in target:
                        expression_driver_components_side.append(component)
                    elif "Right" in target and "30R" in target and "30L" not in target:
                        expression_driver_components_side.append(component)
                else:
                    if not "30" in component:                     
                        expression_driver_components_side.append(component)
            
            elif 'Top' in component:
                expression_driver_components_side.append(component)                
            elif 'Bottom' in component:
                expression_driver_components_side.append(component)
            
            else:
                continue
            
        component_side = target.split('_')[-1]
        component_side_parts = re.findall(r"[A-Z][^A-Z]*", component_side)

        
        if len(component_side_parts) > 1:
            matches = [item for item in expression_driver_components if component_side_parts[1] in item.split('_')]                
            expression_driver_components_side.extend(matches)
        
        self.remove_duplicates_from_list(expression_driver_components_side)
        
        shp_expression = [os.path.join(bs_node, shp) for shp in expression_driver_components_side]
        shp_expression = [shp.replace('\\', '.') for shp in shp_expression]
        shp_expression='*'.join(shp_expression)          
        facial_bs_exp = cmds.expression(name='{}_exp'.format(target),  s='{}.{}={}'.format(bs_node, target, shp_expression))
        cmds.connectAttr('{}.output[0]'.format(facial_bs_exp), '{}.isHistoricallyInteresting'.format(facial_bs_exp), force=1)
        logger.info(facial_bs_exp)
        
            
    def connect_expression(self):
        
        facial_bs_targets = list_shapes(self.blendshape)
        base_shapes = [shp for shp in facial_bs_targets if 'delta' not in shp]            
        corrective_shapes = [shp for shp in facial_bs_targets if 'delta' in shp]
                
        splitting_json, _ = find_latest(self.context.rigs_path / "data", "face_splitter", "json")
        with splitting_json.open() as f:
            data = json.load(f)
               
        splitting_data_shapes = list(data.keys())[0]
        print(splitting_data_shapes)
        print(type(splitting_data_shapes))
        for i in data[splitting_data_shapes]:
            print(i)
            print(type(i))
            for splitting_type, shapes in i.items():
                print(splitting_type)
                print(shapes)
                result = [x for x in base_shapes for y in shapes if y in x]
                self.expression_component_list.append(result)          
       
        for cor_shp in corrective_shapes:
            self.create_facial_bs_expression(self.blendshape, cor_shp)
            

    def cleanup(self):
        
        if cmds.objExists(self.splitting_neutral):
            cmds.delete(self.splitting_neutral)
        
        if cmds.objExists(self.neutral):
            reset_blendshape_targets(self.blendshape)
            delete_history([self.neutral])
        
        self.blendshape = cmds.blendShape(self.neutral, n='facial_bs')[0]
        
        base_shapes = cmds.listRelatives(self.splitted_face_blendshapes_grp)
        base_shapes = sorted(base_shapes)
        for target in base_shapes:
            target = f"{target}"
            if target == self.splitted_face_corrective_blendshapes_grp:
                pass
            else:
                add_blendshape_target(self.blendshape, target)
        
        facial_bs_targets = list_shapes(self.blendshape)
        target_len = len(facial_bs_targets)
        corrective_shapes = cmds.listRelatives(self.splitted_face_corrective_blendshapes_grp)
        for target in corrective_shapes:
            if target not in list_shapes(self.blendshape):
                target = f"{target}"
                add_blendshape_target(self.blendshape, target)
            
        # delete the shapes folder for the split shapes
        if cmds.objExists(self.splitted_face_blendshapes_grp):
            cmds.delete(self.splitted_face_blendshapes_grp)
        if cmds.objExists(self.full_shapes_grp):
            cmds.delete(self.full_shapes_grp)