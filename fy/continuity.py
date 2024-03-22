

from fy.base import BaseTestScene
import numpy as np
import logging
import abc
from utils import * 

class PathParams:
    euler_xyz = [0] * 3
    key_frame_num = [0]
    key_frame_val = [0]


frame_end = 36
frame_mid = int(frame_end) / 2
path_template = [
    {"euler_xyz": [0,0,0],      "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [-25,0,0],    "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,-20,0],    "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,-40,0],    "key_frame_val": [0, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,-60,0],    "key_frame_val": [0, 15],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,20,0],    "key_frame_val": [20, -20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,40,0],    "key_frame_val": [0, -20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,60,0],    "key_frame_val": [0, -15],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,0,0],      "key_frame_val": [-20, 10, -20], "key_frame_num": [0, frame_mid, frame_end]}, 
    {"euler_xyz": [0,0,0],      "key_frame_val": [20, -10, 20], "key_frame_num": [0, frame_mid, frame_end]}, 
    {"euler_xyz": [0,-90,0],      "key_frame_val": [20, 5,  20], "key_frame_num": [0, frame_mid, frame_end]}, 
    # {"euler_xyz": [0,0,0],      "key_frame_val": [-10, 20, -10], "key_frame_num": [0, frame_mid, frame_end]}, 
    # {"euler_xyz": [0,0,0], "key_frame_val": [-20, 20], "key_frame_num": [0, frame_end]}, 
]

class ContinuityTestScene(BaseTestScene):
    """Test scene for ontinuity violation.
    Start: OBJ1 and OBJ2 collide with each other in the air while falling down. OBJ1's velocity is vertical towards ground,
    and OBJ2's velocity is towards OBJ1.
    Normal result: the trajectory of OBJ1 and OBJ2 should follow the laws of physics.
    Violation: the horizontal velocity of both OBJ disappears, and they fall straight down.

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS, path) -> None:
        super().__init__(FLAGS)
        
        # collision parameters
        self.collision_time = 1.0 # second before collision
        self.collision_xy_distance = 2.2 # distance between obj_1 and obj_2 in xy plane
        self.collision_z_distance = 0.1 # distance between obj_1 and obj_2 in z direction
        self.collision_height = 1.5
        self.gravity = [0, 0, -2.8]
        self.scene.gravity = self.gravity

        set_camera_path_constraint_circular(euler_xyz_deg=path["euler_xyz"])
        set_camera_orn_constraint((0, 0, self.table_h))
        set_camera_keyframes(vals=path["key_frame_val"], frames=path["key_frame_num"])

    def generate_keyframes(self):
        """Generate keyframes for the objects, for both violation and non-violation states
        """
        
        # following the laws of physics
        _, collisions = self._run_simulate()

        self.save_test_obj_state("non_violation")

        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)
            
        if self.flags.generate_violation:
            logging.info("Violating the laws of physics")

            # find the first collision frame
            first_collision_frame = 0
            for i in range(len(collisions)):
                instances = collisions[i]['instances']
                if len(instances) == 2:
                    if instances[0] in self.test_obj and instances[1] in self.test_obj:
                        first_collision_frame = int(collisions[i]['frame'])
                        break
            if first_collision_frame == 0:
                raise RuntimeError("No collision detected")

            logging.debug(f"first_collision_frame: {first_collision_frame}")
            
            # make the objects fall straight down after the collision
            for obj in self.test_obj:
                xyz = obj.keyframes["position"][first_collision_frame].copy()
                
                for frame in range(first_collision_frame, self.scene.frame_end+1):
                    # set xy velocity to 0
                    vel = obj.keyframes["velocity"][frame].copy()
                    vel[0] = 0
                    vel[1] = 0
                    obj.velocity = vel
                    obj.keyframe_insert("velocity", frame)

                    # set xy position to the same as the collision frame
                    pos = obj.keyframes["position"][frame].copy()
                    pos[0] = xyz[0]
                    pos[1] = xyz[1]
                    obj.position = pos
                    obj.keyframe_insert("position", frame)
                    
            self.save_test_obj_state("violation")
            
            if self.flags.save_states:
                fname = "violation.blend"
                full_path = self.output_dir / fname
                logging.info("Saving the renderer state to '%s' ",
                            full_path)
                self.renderer.save_state(full_path)

    def generate_keyframes(self):
        """Generate keyframes for the objects, for both violation and non-violation states
        """
        
        # following the laws of physics
        _, collisions = self._run_simulate()

    def add_test_objects(self):
        """Add ? objects

        Returns:
            _type_: _description_
        """
        self.add_background_dynamic_objects(5, 
                                            scale=1, 
                                            x_range=(-1.25, 1.25), 
                                            y_range=(-0.7, 0.7), 
                                            z_range=(3, 3.5))

        # -- add the big object
        big_obj_id = self.rng.choice(self.big_object_asset_id_list)
        big_obj = self.add_object(asset_id=big_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1.25)

        # # -- rotate the object if its principal axis is not aligned with the x axis
        # x_size = big_obj.aabbox[1][0] - big_obj.aabbox[0][0]
        # y_size = big_obj.aabbox[1][1] - big_obj.aabbox[0][1]
        # z_size = big_obj.aabbox[1][1] - big_obj.aabbox[0][1]
        # if y_size < z_size or x_size < z_size:
        #     big_obj.quaternion = kb.Quaternion(axis=[1, 0, 0], degrees=-90) * big_obj.quaternion
        # if (x_size) < (y_size):
        #     big_obj.quaternion = kb.Quaternion(axis=[0, 0, 1], degrees=90) * big_obj.quaternion
        big_obj.position = (0, 0, self.table_h - big_obj.aabbox[0][2])

        # -- add small object
        small_obj_id = self.rng.choice(self.small_object_asset_id_list)
        small_obj = self.add_object(asset_id=small_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1) 
        
        x = np.random.uniform(-0.1, 0.1)
        y = np.random.uniform(big_obj.aabbox[1][1]-small_obj.aabbox[0][1]+0.15, 
                              big_obj.aabbox[1][1]+0.27)
        
        small_obj.position = (x, y, self.table_h - small_obj.aabbox[0][2])

        self.test_obj = [big_obj, small_obj]


        # TODO determine when to make the small object invisible
        # 1. for frame in range(10, 25): bpy.context.scene.frame_set(frame)
        # 2. sample 1000 vertex from the small object and apply ray tracing
        # 3. if we can find a place where < 0.1 -> set the object keyframe
        # 4. otherwise, ...
        
        
        return big_obj, small_obj

        