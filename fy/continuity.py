

from fy.base import BaseTestScene, shapenet_assets
import numpy as np
import logging
import abc
from tqdm import tqdm
import bpy 
from utils import getVisibleVertexFraction, objInFOV
from permanance import PermananceTestScene
import kubric as kb
from utils import align_can_objs, spherical_to_cartesian

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
        self.violation_type = np.random.binomial(n=1,p=0.5)
        self.gravity = (0, 0, -4.9)

        if not(self.violation_type):
            self.default_camera_pos = spherical_to_cartesian()
            self.camera_look_at = (0, 0, self.ref_h)
            self.flags.move_camera = False 
        else:
            self.flags.move_camera = True
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
                # object teletransport
                pos = obj.keyframes["position"][self.frame_violation_start].copy()
                pos[0] += np.random.uniform(0.2, 0.4)
                obj.position = pos
                obj.keyframe_insert("position", self.frame_violation_start)
            
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

        # relocate the block obj
        self.block_obj.position = (0.15, -0.1, self.block_obj.position[2])
        
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
        A valid PermancneTestScene should satisfy the following two conditions
            
            1. include at least one frame in which at least 85% of the test object is occluded
            2. The test object is visible at the first and the last frame

        Args:
            (bool): 
        """

        # TODO: farthest point sampling, try reduce num of samples
        frame_end = self.flags.frame_end

        frame_idx = np.arange(1, frame_end+1)
        visibility = np.zeros_like(frame_idx) * 0.0  
        in_view = np.zeros_like(frame_idx) * 0.0  

        # Check visibility of the test obj at each frame
        print("Checking scene...")
        for i, frame in enumerate(tqdm(range(self.flags.frame_start, self.flags.frame_end))):
            bpy.context.scene.frame_set(frame)
            vis = getVisibleVertexFraction("small_obj", self.rng)
            visibility[i] = vis  

            # Check if the object is in FoV
            in_view[i] = objInFOV("small_obj")

        idx = np.where(np.logical_and(visibility <= 0.1, in_view))[0]     
        frames_violation = frame_idx[idx]

        if self.violation_type:
            cond_1 = len(frames_violation)  # the first condition
            cond_2 = visibility[0] >= 0.15 \
                    and visibility[5] >= 0.15 \
                    and visibility[-6] >= 0.15
            is_valid = cond_2 and cond_1
        else:
            is_valid = in_view[0] and in_view[-5] >= 0.15

        if is_valid:
            # set when the test object is set disappeared  
            self.frame_violation_start =  int(self.rng.uniform(10, 20))
        else:
            print("scene invalid!")

        return is_valid
    
    def _run_simulate(self, save_state=False):
        self.block_obj.static = True
        ret = super()._run_simulate(save_state)
        # reduce the angular velocity at each frame
        obj = self.test_obj[0] # work for only one test obj
        
        xy_axis = [0,1,2]
        # xy_axis.remove(self.test_obj_z_orn) 

        # remove the test object's unexpected rotation

        obj_pos0 = obj.keyframes["position"][0].copy()
        for frame in range(self.scene.frame_start, self.scene.frame_end+1):
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

            # block.velocity = [0,0,0]
            # block.keyframe_insert("velocity", frame)

            # block.angular_velocity = [0,0,0]
            # block.keyframe_insert("angular_velocity", frame)

            # block.position = block_pos0
            # block.keyframe_insert("position", frame)


    #     return ret