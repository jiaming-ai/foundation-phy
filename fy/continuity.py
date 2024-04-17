

from fy.base import BaseTestScene, shapenet_assets
import numpy as np
import logging
import abc
from tqdm import tqdm
import bpy 
from utils import getVisibleVertexFraction, isPointVisible, objInFOV
from permanance import PermananceTestScene
import kubric as kb
from utils import align_can_objs, spherical_to_cartesian

# TODO: test if obj is on the table at most of time; why velocity changes after teletransportation


class ContinuityTestScene(PermananceTestScene):
    """Test scene for permanance violation.
    Start: Object is visible
    Normal result: ...
    Violation: The test object either disappears or teletransports

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS) -> None:

        super().__init__(FLAGS)
        self.frame_violation_start = -1
        # two cases:
        # 1. object disappears
        # 2. object teleports
        self.violation_type = np.random.binomial(n=1,p=0.5)
        self.gravity = (0, 0, -4.9)

        if not(self.violation_type):
            self.default_camera_pos = spherical_to_cartesian(theta_range=[45, 60])
            self.camera_look_at = (0, 0, self.ref_h)
            self.is_move_camera = False
        else:
            self.is_move_camera = True
    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()

        if not(self.violation_type):
            # remove block object
            self.block_obj.position = (0, 0, -10)


    def generate_keyframes(self):
        """Generate keyframes for the test objects, for both violation and non-violation states
        """
        # _, collisions = self._run_simulate()
        # # following the laws of physics
        # self.save_non_violation_scene()
        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)

        

        for obj in self.test_obj: # works for only 1 object!
            # linear interpolation
            logging.info("Violation start at '%d' ",
                        self.frame_violation_start)
            if self.violation_type:
                # object disappear
                for frame in range(int(self.frame_violation_start), self.scene.frame_end+1):
                    # set negative z position 
                    pos = obj.keyframes["position"][frame].copy()
                    pos[2] = -1
                    obj.position = pos
                    obj.keyframe_insert("position", frame)
            else:
                # save the states of bg objs
                bg_states = []
                for bgobj in self.dynamic_objs:
                    state = self.get_object_keyframes(bgobj)
                    bg_states.append(state)

                # object teletransport
                vel = obj.keyframes["velocity"][self.frame_violation_start].copy()
                obj.velocity = vel
                obj.keyframe_insert("velocity", self.frame_violation_start)
                
                pos = obj.keyframes["position"][self.frame_violation_start].copy()
                pos[0] += np.random.uniform(0.2, 0.3)
                obj.position = pos
                obj.keyframe_insert("position", self.frame_violation_start)


                self._run_simulate(frame_start=self.frame_violation_start)
                for i, bgobj in enumerate(self.dynamic_objs):
                    self.set_object_keyframes(bgobj, bg_states[i])
            
            self.save_violation_scene()
            
            if self.flags.save_states:
                fname = "violation.blend"
                full_path = self.output_dir / fname
                logging.info("Saving the renderer state to '%s' ",
                            full_path)
                self.renderer.save_state(full_path)

    def add_test_objects(self):
        """Add one small object
        Returns:
            _type_: _description_
        """
        # -- add small object
        print("adding the small object")

        if self.violation_type:
            # relocate the block obj
            self.block_obj.position = (0.15, -0.1, self.block_obj.position[2])
        else:
            self.block_obj.position = (0, 0, -10)
        # initialize the obj. Note the the initial position should be (0,0,0) 
        # so that the dist between its CoM and the table surface can be calculated
        small_obj_id = [name for name, spec in shapenet_assets._assets.items()
                if spec["metadata"]["category"] == "can"]
        small_obj_id = self.rng.choice(small_obj_id)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(0, 0, 0),
                                velocity=(0, 0, 0),
                                quaternion=kb.Quaternion(axis=[0, 0, 1], degrees=0),
                                is_dynamic=True,
                                scale=0.15, 
                                name="small_obj") 
        
        self.test_obj_z_orn = align_can_objs(small_obj)
        

        # set the position of the can to avoid potential collision 
        # of the block object
        table_x_range = self.table.aabbox[0][0]
        block_y_range = self.block_obj.aabbox[1][1]
        vx = self.rng.uniform(0.8, 1.0) # initial velocitry
        px = self.rng.uniform(0, 0.05) + small_obj.aabbox[1][2] + table_x_range # initial position
        py = self.rng.uniform(0.1, 0.15) + block_y_range
        pz = self.rng.uniform(0.0, 0.01) + self.ref_h - small_obj.aabbox[0][2]
        small_obj.position = (px, py, pz)
        small_obj.velocity = (vx, 0, 0)
        small_obj.friction = 0.1


        # align the can object

        # small_obj.position = (-0.8, 0.15, self.ref_h+0.2)
        # for _ in range(10):
        #     print(small_obj.position, self.ref_h, small_obj.aabbox[0][2], self.ref_h - small_obj.aabbox[0][2])
        #     print(small_obj.aabbox)
        self.test_obj = [small_obj]
        self._run_simulate()
        self.save_non_violation_scene()
        return small_obj

   
            
            
    def _check_scene(self):
        """ Check whether the scene is valid. 
        A valid...

        Args:
            (bool): 
        """

        # TODO: farthest point sampling, try reduce num of samples
        frame_end = self.flags.frame_end

        frame_idx = np.arange(1, frame_end+1)
        visibility_obj = np.zeros_like(frame_idx) * 0.0  
        visibility_table = np.ones_like(frame_idx) * 1.0 
        in_view = np.zeros_like(frame_idx) * 0.0  
        obj_on_table = np.ones_like(frame_idx) * 1.0  

        # Check visibility of the test obj at each frame
        print("Checking scene...")
        obj = self.test_obj[0] # work for only one test obj
        for i, frame in enumerate(tqdm(range(self.flags.frame_start, self.flags.frame_end))):
            bpy.context.scene.frame_set(frame)
            vis_obj = getVisibleVertexFraction("small_obj", self.rng)
            vis_table = isPointVisible([0, 0, self.ref_h], [self.table_name, self.block_name, "small_obj"])
            visibility_obj[i] = vis_obj  
            visibility_table[i] = vis_table
            obj_on_table[i] = obj.keyframes["position"][frame][2] > self.ref_h-0.05

            # Check if the object is in FoV
            in_view[i] = objInFOV("small_obj")

        is_table_visible = visibility_table >= 0.15
        idx = np.where(np.logical_and(visibility_obj >= 0.15, in_view))[0]     
        frames_violation = frame_idx[idx]

        if self.violation_type:
            cond_1 = len(frames_violation)  # the first condition
            cond_2 = visibility_obj[0] >= 0.15 \
                    and visibility_obj[5] >= 0.15 \
                    and visibility_obj[-6] >= 0.15
            cond = [cond_2,
                    cond_1,
                    in_view[0],
                    in_view[5],
                    in_view[-12],
                    is_table_visible[6:-6].min(), 
                    obj_on_table.sum() >= 25]
        else:
            cond = [visibility_obj[0] >= 0.5,
                    in_view[0],
                    in_view[-5],
                    is_table_visible[6:-6].min(), 
                    obj_on_table.sum() >= 25]

        is_valid = np.min(cond)
        if is_valid:
            # set when the test object is set disappeared  
            if self.violation_type:
                self.frame_violation_start = int((frames_violation[0]+frames_violation[-1])/2) 
            else:
                self.frame_violation_start =  int(self.rng.uniform(7, 17)) 
                                    
        else:
            if self.flags.debug:
                logging.warning("Invalid scene data")
                logging.warning(cond)

        return is_valid
    
    def _run_simulate(self, save_state=False, frame_start=0):
        self.block_obj.static = True
        ret = super()._run_simulate(save_state, frame_start=frame_start)

        obj = self.test_obj[0] # work for only one test obj

        # remove the test object's unexpected rotation
        obj_pos0 = obj.keyframes["position"][frame_start].copy()
        for frame in range(frame_start, self.scene.frame_end+1):
            # set xy velocity to 0
            q = obj.keyframes["quaternion"][frame].copy()
            q = np.array(q)
            q[1] = 0
            q[3] = 0
            obj.quaternion = q
            obj.keyframe_insert("quaternion", frame)

            pos = obj.keyframes["position"][frame].copy()
            pos[1] = obj_pos0[1] 
            obj.position = pos
            obj.keyframe_insert("position", frame)

            vel = obj.keyframes["velocity"][frame].copy()
            vel[1] = 0
            obj.velocity = vel
            obj.keyframe_insert("velocity", frame)
        return ret

            # block.velocity = [0,0,0]
            # block.keyframe_insert("velocity", frame)

            # block.angular_velocity = [0,0,0]
            # block.keyframe_insert("angular_velocity", frame)

            # block.position = block_pos0
            # block.keyframe_insert("position", frame)


    #     return ret