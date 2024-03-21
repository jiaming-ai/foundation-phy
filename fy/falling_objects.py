

from fy.base import BaseTestScene
import numpy as np
import logging
import abc
class FallingObjectTestScene(BaseTestScene):
    """Base class for falling object test scene"""

    def __init__(self, FLAGS) -> None:
        super().__init__(FLAGS)
        
        # collision parameters
        self.collision_time = 1.0 # second before collision
        self.collision_xy_distance = 2.2 # distance between obj_1 and obj_2 in xy plane
        self.collision_z_distance = 0.1 # distance between obj_1 and obj_2 in z direction
        self.collision_height = 1.5
        self.gravity = [0, 0, -2.8]
        self.scene.gravity = self.gravity

        # look at a fixed height
        self.scene.camera.position = (0, -5, 1.7)
        self.scene.camera.look_at([0, 0, self.collision_height])


    def add_single_object(self):
        """Add a single object to the scene

        Returns:
            _type_: _description_
        """
        obj_id = self.rng.choice(self.small_object_asset_id_list)
        pos = self.rng.normal(0, 0.2, 3)
        pos[2] += self.collision_height
        vel = [0, 0, 0]
        obj = self.add_dynamic_object(asset_id=obj_id,
                                       position=pos, 
                                       velocity=vel,
                                       scale=1.8)
        return obj
    
    def add_colliding_objects(self):
        """Add two colliding objects

        Returns:
            _type_: _description_
        """
        g = -self.gravity[2]
        t = self.collision_time # second
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
        obj_1 = self.add_dynamic_object(asset_id=obj_1_id,
                                           position=pos_1, 
                                           velocity=vel_1_xyz,
                                           scale=1.8)
        
        obj_2_id = self.rng.choice(self.big_object_asset_id_list)
        obj_2 = self.add_dynamic_object(asset_id=obj_2_id,
                                           position=pos_2, 
                                           velocity=vel_2_xyz,
                                           scale=2.8)
        
        self.test_obj = [obj_1, obj_2]
        
        return obj_1, obj_2
   
  