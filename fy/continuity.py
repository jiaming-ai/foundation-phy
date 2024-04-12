

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
        
    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()
        
        # remove block object
        self.block_obj.position = (0, 0, -10)

        self.scene.camera.position = spherical_to_cartesian()
        self.scene.camera.look_at = (0, 0, self.ref_h)

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
            if np.random.binomial(n=1,p=0.5):
                for frame in range(int(self.frame_violation_start), self.scene.frame_end+1):
                    # set negative z position 
                    pos = obj.keyframes["position"][frame].copy()
                    pos[2] = -1
                    obj.position = pos
                    obj.keyframe_insert("position", frame)
            else:
                pos = obj.keyframes["position"][self.frame_violation_start].copy()
                pos[0] += np.random.uniform(0.2, 0.4)
                obj.position = pos
                obj.keyframe_insert("position", self.frame_violation_start)
                self._run_simulate(frame_start=self.frame_violation_start)
            
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
        table_x_range = self.table.aabbox[0][0]
        vx = self.rng.uniform(1, 1.5) # initial velocitry
        px = self.rng.uniform(table_x_range-0.5, table_x_range) # initial position
        pz = self.rng.uniform(0.2, 0.4) + self.h
        # -- add small object
        print("adding the small object")
        self.block_obj.position = (0, -0.1, self.block_obj.position[2])
        small_obj_id = [name for name, spec in shapenet_assets._assets.items()
                if spec["metadata"]["category"] == "can"]
        small_obj_id = self.rng.choice(small_obj_id)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(px, 0.15*0, pz),
                                velocity=(vx, 0, 0),
                                quaternion=kb.Quaternion(axis=[0, 0, 1], degrees=0),
                                is_dynamic=True,
                                scale=0.15, 
                                name="small_obj") 
        
        # align the can object
        align_can_objs(small_obj)

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

        cond_1 = len(frames_violation)  # the first condition
        cond_2 = visibility[0] >= 0.15 and visibility[-1] >= 0.15
        is_valid = cond_2 and cond_1

        if is_valid:
            # set when the test object is set disappeared  
            self.frame_violation_start =  int(0.1*frames_violation[0]+0.9*frames_violation[-1])
        else:
            print("scene invalid!")

        return is_valid