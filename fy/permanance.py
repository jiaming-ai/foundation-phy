

from fy.base import BaseTestScene
import numpy as np
import logging
import abc
from tqdm import tqdm
import bpy 
from utils import getVisibleVertexFraction, objInFOV

class PermananceTestScene(BaseTestScene):
    """Test scene for permanance violation.
    Start: Object is visible
    Normal result: ...
    Violation: The test object disappears

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS) -> None:

        super().__init__(FLAGS)
        self.frame_violation_start = -1
        
    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()
    
    def generate_keyframes(self):
        """Generate keyframes for the test objects, for both violation and non-violation states
        """
        _, collisions = self._run_simulate()
        # following the laws of physics
        self.save_non_violation_scene()

        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)
            

        for obj in self.test_obj:
            # linear interpolation
            
            for frame in range(int(self.frame_violation_start), self.scene.frame_end+1):
                # set negative z position 
                pos = obj.keyframes["position"][frame].copy()
                pos[2] = -1
                obj.position = pos
                obj.keyframe_insert("position", frame)

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
        small_obj_id = self.rng.choice(self.super_small_object_asset_id_list)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=0.5, 
                                name="small_obj") 
        
        x = np.random.uniform(-0.1, 0.1)
        y = np.random.uniform(self.block_obj.aabbox[1][1]-small_obj.aabbox[0][1]+0.1, 
                              self.block_obj.aabbox[1][1]+0.20)
        
        small_obj.position = (x, y, self.ref_h - small_obj.aabbox[0][2])

        self.test_obj = [small_obj]
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
        for i, frame in enumerate(tqdm(frame_idx)):
            bpy.context.scene.frame_set(frame)
            vis = getVisibleVertexFraction("small_obj", self.rng)
            visibility[i] = vis  

            # Check if the object is in FoV
            in_view[i] = objInFOV("small_obj")

        idx = np.where(np.logical_and(visibility <= 0.1, in_view))[0]     
        frames_violation = frame_idx[idx]

        cond_1 = len(frames_violation)  # the first condition
        cond_2 = visibility[0] >= 0.15 and visibility[-1] >= 0.15
        is_valid = cond_1 and cond_2

        if is_valid:
            # set when the test object is set disappeared  
            self.frame_violation_start =  int((frames_violation[0]+frames_violation[-1])/2)
        else:
            print("scene invalid!")

        return is_valid