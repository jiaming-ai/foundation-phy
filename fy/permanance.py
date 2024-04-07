

from fy.base import BaseTestScene
import numpy as np
import logging
import abc

## TODO: 1. valid scene; 2. set when the object disappears
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
        

    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()
        


    def generate_keyframes(self):
        """Generate keyframes for the objects, for both violation and non-violation states
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
            
        # make the objects disappeared
        first_disappear_frame = 10 ## TODO: calculate this
        for obj in self.test_obj:
            # linear interpolation
            xyz = obj.get_value_at("position", first_disappear_frame, interpolation="linear").copy()
            
            for frame in range(int(first_disappear_frame), self.scene.frame_end+1):
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
        """Add two colliding objects

        Returns:
            _type_: _description_
        """
        print("adding big object")
        # -- add the big object
        big_obj_id = self.rng.choice(self.super_big_object_asset_id_list)
        big_obj = self.add_object(asset_id=big_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1.25)
        
        big_obj.position = (0, 0, self.ref_h - big_obj.aabbox[0][2])

        # -- add small object
        print("adding small object")
        small_obj_id = self.rng.choice(self.super_small_object_asset_id_list)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1, 
                                name="small_obj") 
        
        x = np.random.uniform(-0.1, 0.1)
        y = np.random.uniform(big_obj.aabbox[1][1]-small_obj.aabbox[0][1]+0.1, 
                              big_obj.aabbox[1][1]+0.20)
        
        small_obj.position = (x, y, self.ref_h - small_obj.aabbox[0][2])

        self.test_obj = [big_obj, small_obj]
        return big_obj, small_obj

        