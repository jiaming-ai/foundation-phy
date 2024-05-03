

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
invalid_small_objs = ["02946921/f8fd565d00a7a6f9fef1ca8c5a3d2e08", 
                      "02946921/343287cd508a798d38df439574e01b2", 
                      "02946921/91a524cc9c9be4872999f92861cdea7a",
                      "02946921/4d4fc73864844dad1ceb7b8cc3792fd", 
                      "02946921/19fa6044dd31aa8e9487fa707cec1558",
                      "02946921/129880fda38f3f2ba1ab68e159bfb347",
                      "02946921/7b643c8136a720d9db4a36333be9155",
                      ]

class ContinuityTestScene(BaseTestScene):
    """Test scene for permanance violation.
    Start: Object is visible
    Normal result: ...
    Violation: The test object either disappears or teletransports

    Args:
        BaseTestScene (_type_): _description_
    """
    
    def __init__(self, FLAGS) -> None:
        super().__init__(FLAGS)
        self.is_add_background_static_objects = False
        self.frame_violation_start = -1
        # two cases:
        # 1. object disappears
        # 0. object teleports
        self.violation_type = 1#np.random.binomial(n=1,p=0.5)
        self.is_move_camera = np.random.binomial(n=1,p=0.5)
        self.gravity = (0, 0, -4.9)

        # self.back_camera_pos = spherical_to_cartesian(r_range=[2.25, 2.75], theta_range=[70, 80], phi_range=[-45+180, 45+180])
        self.alternative_camera_pos = spherical_to_cartesian(r_range=[1.5, 2.25], theta_range=[70, 80], phi_range=[-45+180, 45+180])
        

        # if not(self.violation_type):
        #     self.default_camera_pos = spherical_to_cartesian(r_range=[2, 3], theta_range=[75, 85])
        #     self.camera_look_at = (0, 0, self.ref_h)
        #     # self.flags.is_move_camera = False 
        # else:
        #     # self.flags.is_move_camera = True
        #     pass

        

    def prepare_scene(self):
        print("preparing scene ...")
        super().prepare_scene()
        self.alternative_camera_pos[2] += self.ref_h
        self.default_camera_pos[2] += self.ref_h
        self.camera_look_at = (0, 0, self.ref_h)
        self.alternative_camera_look_at = (0, 0, self.ref_h)

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
                pos[0] += np.random.uniform(0.5, 0.65)
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
        valid = False
        small_obj = None
        while not valid: # only select valid small object
            print("adding the small object")
            if small_obj is not None:
                self.scene.remove(small_obj)

            if self.violation_type:
                # relocate the block obj
                self.block_obj.position = (0.15, -0.1, self.block_obj.position[2])
            else:
                self.block_obj.position = (0, 0, -10)
            # initialize the obj. Note the the initial position should be (0,0,0) 
            # so that the dist between its CoM and the table surface can be calculated
            small_obj_id_all = [name for name, spec in shapenet_assets._assets.items()
                    if spec["metadata"]["category"] == "can"]
            small_obj_id = [id for id in small_obj_id_all if id not in invalid_small_objs]
            small_obj_id = self.rng.choice(small_obj_id)
            small_obj = self.add_object(asset_id=small_obj_id,
                                    position=(0, 0, 0),
                                    velocity=(0, 0, 0),
                                    quaternion=kb.Quaternion(axis=[0, 0, 1], degrees=0),
                                    is_dynamic=True,
                                    scale=0.15, 
                                    name="small_obj") 
            
            self.test_obj_z_orn, radius, _, valid = align_can_objs(small_obj)
            self.radius = radius
        # small_obj.quaternion =  kb.Quaternion(axis=[0, 0, 1], degrees=180) * small_obj.quaternion

        # set the position of the can to avoid potential collision 
        # of the block object
        table_x_range = self.table.aabbox[0][0]
        block_y_range = self.block_obj.aabbox[1][1]
        vx = self.rng.uniform(0.35, 0.8) # initial velocitry
        px = self.rng.uniform(0, 0.05) + small_obj.aabbox[1][2] + table_x_range # initial position
        py = self.rng.uniform(0.1, 0.15) + block_y_range
        pz = self.rng.uniform(0.05, 0.1) + self.ref_h + radius
        small_obj.position = (px, py, pz)
        small_obj.velocity = (vx, 0, 0)
        small_obj.friction = 0

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
        # self.frame_violation_start = 20; return True
        less_strict = not(self.flags.render_violate_video) 
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
        for i, frame in enumerate((range(self.flags.frame_start, self.flags.frame_end))):
            bpy.context.scene.frame_set(frame)
            vis_obj = getVisibleVertexFraction("small_obj", self.rng, "camera")
            vis_table = isPointVisible([0, 0, self.ref_h], [self.table_name, self.block_name, "small_obj"], "camera")
            visibility_obj[i] = vis_obj  
            visibility_table[i] = vis_table
            obj_on_table[i] = obj.keyframes["position"][frame][2] > self.ref_h-0.05

            # Check if the object is in FoV
            in_view[i] = objInFOV("small_obj")

        is_table_visible = visibility_table >= 0.15
        idx = np.where(np.logical_and(visibility_obj >= 0.15, in_view))[0]     
        frames_violation = frame_idx[idx]

        is_obj_visible = visibility_obj >= 0.35
        if self.violation_type:
            cond_1 = len(frames_violation)  # the first condition
            # cond_2 = visibility_obj[0] >= 0.15 \
            #         and visibility_obj[5] >= 0.15 \
            #         and visibility_obj[-6] >= 0.15
            if less_strict:
                cond_2 = is_obj_visible[:10].max() and is_obj_visible[-10:].max()
            else:
                cond_2 = is_obj_visible[:6].max() and is_obj_visible[-7:].max()
            
            cond = [cond_2,
                    cond_1 or less_strict,
                    in_view[0],
                    in_view[5],
                    in_view[-12:].max()  or less_strict,
                    is_table_visible[6:-6].min(), 
                    obj_on_table.sum() >= 16  or less_strict
                    ]
            
        else:
            cond = [visibility_obj[0] >= 0.5,
                    in_view[0],
                    in_view[-5]  or less_strict,
                    is_table_visible[6:-6].min(), 
                    obj_on_table.sum() >= 20  or less_strict
                    ]

        is_valid = np.min(cond)
        logging.error(cond)
        # logging.error(np.min(cond))
        # logging.error(is_obj_visible[:10])
        # logging.error( is_obj_visible[-10:])
        if is_valid:
            # set when the test object is set disappeared  
            if self.violation_type:
                if frames_violation.min() > 0: 
                    self.frame_violation_start = int((frames_violation[0]+frames_violation[-1])/2) 
                else:
                    # randomly sample a index corresponding to an arbitrary non-zero element
                    nonzero_indices = np.nonzero(frames_violation)[0] 
                    # if len(nonzero_indices >= 3):
                    #     nonzero_indices = nonzero_indices[1:-1] # remove the first and the last element
                    random_nonzero_index = int(len(nonzero_indices) / 2)# np.random.choice(nonzero_indices)
                    self.frame_violation_start = random_nonzero_index
                
            else:
                self.frame_violation_start =  int(self.rng.uniform(4, 12)) 
                                    
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
            pos = obj.keyframes["position"][frame].copy()

            rot_angle = (obj_pos0[0] - pos[0]) / self.radius
            quaternion = kb.Quaternion(axis=[0, 1, 0], degrees=-rot_angle * 180 / np.pi)
            # print(self.radius, (obj_pos0[0] - pos[0]), rot_angle * 180 / np.pi)
            obj.quaternion = quaternion
            obj.keyframe_insert("quaternion", frame)
        return ret
        for frame in range(frame_start, self.scene.frame_end+1):
            # set xy velocity to 0
            q = obj.keyframes["quaternion"][frame].copy()
            q = np.array(q)
            q[1] = 0
            q[3] = 0
            q[2] = -q[2]
            obj.quaternion = q / np.linalg.norm(q)
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