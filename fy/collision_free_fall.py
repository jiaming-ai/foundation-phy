

from fy.base import BaseTestScene
import numpy as np
import logging
import abc
from utils import spherical_to_cartesian, getVisibleVertexFraction
import bpy

class CollisionScene(BaseTestScene):
    """Test scene for collision violation.
    Start: OBJ1 and OBJ2 collide with each other in the air while falling down. OBJ1's velocity is vertical towards ground,
    and OBJ2's velocity is towards OBJ1.
    Normal result: the trajectory of OBJ1 and OBJ2 should follow the laws of physics.
    Violation: the horizontal velocity of both OBJ disappears, and they fall straight down.

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS) -> None:
        
        super().__init__(FLAGS)
        # collision parameters
        self.first_collision_frame = 0
        self.violation_time = 1.0 # second before collision
        self.collision_xy_distance = 2.2 # distance between obj_1 and obj_2 in xy plane
        self.collision_z_distance = 0.1 # distance between obj_1 and obj_2 in z direction
        self.collision_height = 1.2
        self.gravity = [0, 0, -2.8]

        # look at a fixed height
        # self.scene.camera.position = (0, -5, 1.7)
        # self.default_camera_pos = spherical_to_cartesian(r_range=[2.5, 3], theta_range=[89, 91], phi_range=[-5, 5]) # (0, -1, 1.7)
        self.camera_look_at = [0, 0, self.collision_height]
        # self.default_camera_pos[2] += self.collision_height
        self.default_camera_pos = [0, -5, 1.7]

        self.is_move_camera = False
        self.is_add_block_objects = False
        self.is_add_table = True
        
        
    def prepare_scene(self):
        super().prepare_scene()
        self.scene.gravity = self.gravity

        # # look at a fixed height
        # self.scene.camera.position = (0, -5, 1.7)
        # self.scene.camera.look_at([0, 0, self.collision_height])

    def generate_keyframes(self):
        """Generate keyframes for the objects, for both violation and non-violation states
        """
        
        # following the laws of physics
        _, collisions = self._run_simulate()

        self.save_non_violation_scene()

        if self.flags.save_states:
            fname = "non_violation.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)
            
        if self.flags.generate_violation:
            logging.info("Generating scene with violation of laws of physics")

            # find the first collision frame
            first_collision_frame = 0
            for i in range(len(collisions)):
                instances = collisions[i]['instances']
                if len(instances) == 2:
                    if instances[0] in self.test_obj and instances[1] in self.test_obj:
                        first_collision_frame = collisions[i]['frame']
                        break
            if first_collision_frame == 0:
                raise RuntimeError("No collision detected")

            self.first_collision_frame = first_collision_frame
            logging.debug(f"first_collision_frame: {first_collision_frame}")
            
            # make the objects fall straight down after the collision
            for obj in self.test_obj:
                # linear interpolation
                xyz = obj.get_value_at("position", first_collision_frame, interpolation="linear").copy()
                
                for frame in range(int(first_collision_frame), self.scene.frame_end+1):
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
        g = -self.gravity[2]
        t = self.violation_time # second
        z_dis_before_collision = g * t ** 2 / 2
        obj_dist = self.collision_xy_distance # distance between obj_1 and obj_2 in xy plane
        pos_2_delta_z = self.collision_z_distance # distance between obj_1 and obj_2 in z direction
        
        pos_1 = self.rng.normal(0, 0.2, 3)
        pos_1[2] += self.collision_height + z_dis_before_collision
        vel_1_xyz = [0, 0, 0]
        logging.debug(f"pos_1: {pos_1}, vel_1_xyz: {vel_1_xyz}")
        
        collision_z = pos_1[2] - z_dis_before_collision
        collision_xyz = [pos_1[0], pos_1[1], collision_z]
        logging.debug(f"s before collision: {z_dis_before_collision}, t: {t}, collision_xyz: {collision_xyz}")
        
        pos_2 = self.rng.normal(0, 0.1, 3)
        theta = self.rng.uniform(-np.pi/8, np.pi/8)
        theta = self.rng.choice([0,1]) * np.pi + theta
        pos_2[0] += obj_dist * np.cos(theta)
        pos_2[1] += obj_dist * np.sin(theta)
        pos_2[2] += pos_1[2] + pos_2_delta_z
        logging.debug(f"pos_2: {pos_2}")
        vel_2_xy = np.array(pos_1[:2]) - np.array(pos_2[:2]) / t
        vel_2_z= -(pos_2_delta_z+0.02) / t
        vel_2_xyz = [vel_2_xy[0], vel_2_xy[1], vel_2_z]
        
        # random select two objects, consider the exclusion list
        obj_1_id = self.rng.choice(self.small_object_asset_id_list)
        obj_1 = self.add_object(asset_id=obj_1_id,
                                           position=pos_1, 
                                           velocity=vel_1_xyz,
                                           scale=1.0, 
                                           name="small_obj") # 1.8
        
        obj_2_id = self.rng.choice(self.big_object_asset_id_list)
        obj_2 = self.add_object(asset_id=obj_2_id,
                                           position=pos_2, 
                                           velocity=vel_2_xyz,
                                           scale=1.2, 
                                           name="big_obj") # 2.8
        
        self.test_obj = [obj_1, obj_2]
        
        return obj_1, obj_2
    