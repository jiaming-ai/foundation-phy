

from fy.base import BaseTestScene, shapenet_assets
import numpy as np
import logging
import abc
from tqdm import tqdm
import bpy 
from utils import getVisibleVertexFraction, objInFOV
import kubric as kb
from utils import align_can_objs, spherical_to_cartesian
from copy import deepcopy

class SupportTestScene(BaseTestScene):
    """Test scene for permanance violation.
    Start: Object is visible
    Normal result: ...
    Violation: The test object wither pass through table or stops in air

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS) -> None:

        super().__init__(FLAGS)
        self.frame_violation_start = 10
        self.initial_dist_to_table = 0
        self.violation_type = 0#np.random.binomial(n=1,p=0.5)
        self.gravity = [0, 0, -1.5]
        self.flags.move_camera = False

        self.default_camera_pos = spherical_to_cartesian()
        
        
        
    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()
        self.scene.gravity = self.gravity

        self.renderer.save_state(f"temp_scene/cam.blend")

    def generate_keyframes(self):
        if self.violation_type:
            self.generate_keyframes_type_1()
        else:
            self.generate_keyframes_type_0()
            
    def generate_keyframes_type_1(self):
        """Generate keyframes for the test objects, for both violation and non-violation states
        """
        _, collisions = self._run_simulate()
        # # following the laws of physics
        self.save_non_violation_scene()
        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)

        
        # two cases: 1. pass through table 2. stops
        # set when test object stops moving
    
        for obj in self.test_obj:
            # linear interpolation
            self.frame_violation_start = 10# int(self.flags.frame_rate * \
                                                #   np.sqrt(2/9.8 * self.initial_dist_to_table)) 

            # get the violation frame
            for i in range(self.scene.frame_end+1):
                pos_z = obj.keyframes["position"][i][2]
                logging.error((i, pos_z, self.ref_h, pos_z - self.ref_h))
                if pos_z - self.ref_h <= 0.2:
                    self.frame_violation_start = i
                    break
                

            logging.info("Violation start at '%d' ",
                        self.frame_violation_start)

            for frame in range(int(self.frame_violation_start), self.scene.frame_end+1):
                obj.position = obj.keyframes["position"][self.frame_violation_start]
                obj.keyframe_insert("position", frame)
                

            self.save_violation_scene() 
            
            if self.flags.save_states:
                fname = "violation.blend"
                full_path = self.output_dir / fname
                logging.info("Saving the renderer state to '%s' ",
                            full_path)
                self.renderer.save_state(full_path)

    def generate_keyframes_type_0(self):

        self._run_simulate()
        self.save_non_violation_scene()
        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)

        bg_states = []
        for obj in self.dynamic_objs:
            state = self.get_object_keyframes(obj)
            bg_states.append(state)

        self.load_non_violation_scene()
        for obj in self.test_obj:
            pos = obj.keyframes["position"][0].copy()
            obj.position = pos
            obj.keyframe_insert("position", 0)
        self.hide_table()
        self._run_simulate()
        # fname = "temp.blend"
        # full_path = self.output_dir / fname
        # logging.info("Saving the renderer state to '%s' ",
        #             full_path)
        # self.renderer.save_state(full_path)
        self.save_violation_scene()
        self.recover_table()

        for i, obj in enumerate(self.dynamic_objs):
            self.set_object_keyframes(obj, bg_states[i])

        # self._run_simulate()
        # self.load_violation_scene()

        if self.flags.save_states:
            fname = "violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)

        
    def hide_table(self):
        for frame in range(self.scene.frame_end+1):
            pos = self.table.keyframes["position"][frame].copy()
            pos[2] -= 10
            self.table.position = pos
            self.table.keyframe_insert("position", frame)

    def recover_table(self):
        for frame in range(self.scene.frame_end+1):
            pos = self.table.keyframes["position"][frame].copy()
            pos[2] += 10
            self.table.position = pos
            self.table.keyframe_insert("position", frame)

    def add_test_objects(self):
        """Add one small object
        Returns:
            _type_: _description_
        """
        # remove block object
        self.block_obj.position = (0, 0, -10)
        # -- add small object
        print("adding the small object")
        small_obj_id = self.rng.choice(self.super_big_object_asset_id_list)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1, 
                                name="small_obj")
        
        # align the can object
        align_can_objs(small_obj)
        self.initial_dist_to_table = np.random.uniform(0.5, 1)
        z = self.initial_dist_to_table + self.ref_h
        
        table_x_range = (self.table.aabbox[0][0], self.table.aabbox[1][0])
        table_y_range = (self.table.aabbox[0][1], self.table.aabbox[1][1])

        if self.violation_type:
            # set the x_pos of the test object (either side of the table)
            x_disp_pos = self.rng.uniform(0, 0.05) + self.table.aabbox[1][0]
            x_disp_neg = self.rng.uniform(-0.05, 0) + self.table.aabbox[0][0]
            x_disp = self.rng.choice([x_disp_pos, x_disp_neg])
            x_pos = x_disp
            small_obj.position = (x_pos, 0, z)
            self.camera_look_at = (x_pos, 0, self.ref_h)
        else:
            small_obj.position = (0, 0, z)
        # for _ in range(10):
        #     print(small_obj.position, self.ref_h, small_obj.aabbox[0][2], self.ref_h - small_obj.aabbox[0][2])
        #     print(small_obj.aabbox)
        self.test_obj = [small_obj]

        if self._check_scene():
            self.add_background_dynamic_objects(5, 
                                            scale=0.8,
                                            x_range=table_x_range, 
                                            y_range=table_y_range,
                                            z_range=(z, z),
                                            set_rand_vel=False,
                                            )
        

        
        return small_obj
    

    def _check_scene(self):
        # frame_end = self.flags.frame_end
        # frame_start = 5

        # visibility = np.zeros(2) * 0.0  
        # in_view = np.zeros(2) * 0.0 

        # # Check visibility of the test obj at each frame
        # print("Checking scene...")
        # for i, frame in enumerate([frame_start, frame_end]):
        #     bpy.context.scene.frame_set(frame)
        #     vis = getVisibleVertexFraction(self.table_name, self.rng)
        #     visibility[i] = vis  

        #     # Check if the object is in FoV
        #     # in_view[i] = objInFOV("small_obj")

        # # return (visibility[0] >= 0.15 
        # #     and visibility[-1] >= 0.15
        # #     # and in_view[0]
        # #     # and in_view[1]
        # #     )

        test_frame = 10
        obj = self.test_obj[0]
        obj_pos0 = obj.position 
        obj_h  = obj.aabbox[1][2] - obj.aabbox[0][2]
        test_z = [obj_pos0[2], self.ref_h+obj_h, obj_h]
        visibility = np.zeros(len(test_z)) * 0.0
        
        for i, pos_z in enumerate(test_z):
            # set the object to the test position
            pos = obj_pos0.copy()
            pos[2] = pos_z
            obj.position = pos
            obj.keyframe_insert("position", test_frame)
            
            # go to the test frame in blender and apply ray tracing
            bpy.context.scene.frame_set(test_frame)
            vis = getVisibleVertexFraction("small_obj", self.rng)
            visibility[i] = (vis >= 0.5)

        if self.violation_type:
            visibility[-1] = 1
        obj.position = obj_pos0
        obj.keyframe_insert("position", 0)

        return visibility.min()

        


    