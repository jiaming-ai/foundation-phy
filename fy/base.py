
import logging
import bpy
import kubric as kb
from kubric.simulator import PyBullet
from kubric.renderer import Blender
import numpy as np
import os
import abc
from etils import epath
from kubric import core
from kubric.core import color
import random
from scipy.spatial.transform import Rotation
from utils import *



# --- Some configuration values
# the region in which to place objects [(min), (max)]
STATIC_SPAWN_REGION = [(-4, -1, 0), (4, 7, 10)] # for static objects
DYNAMIC_SPAWN_REGION = [(-5, -5, 1), (5, 5, 5)]
VELOCITY_RANGE = [(-4., -4., 0.), (4., 4., 0.)]

SCENE_EXCLUDE = ["wobbly_bridge"]

print("loading shapenet")
shapenet_assets = kb.AssetSource.from_manifest("gs://kubric-unlisted/assets/ShapeNetCore.v2.json")
print("loading gso")
gso_assets = kb.AssetSource.from_manifest("gs://kubric-public/assets/GSO/GSO.json")
print("loading kubasic")
kubasic_assets = kb.AssetSource.from_manifest("gs://kubric-public/assets/KuBasic/KuBasic.json")
print("loading hdri")
hdri_assets = kb.AssetSource.from_manifest("gs://kubric-public/assets/HDRI_haven/HDRI_haven.json")
print("finished loading all the sources")

# TODO
frame_mid = 18
frame_end = 36
path_template = [
    {"euler_xyz": [0,0,0],      "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [-25,0,0],    "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, # !
    {"euler_xyz": [0,-20,0],    "key_frame_val": [-20, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,-40,0],    "key_frame_val": [-15, 20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,-60,0],    "key_frame_val": [-10, 15],      "key_frame_num": [0, frame_end]}, # !
    {"euler_xyz": [0,20,0],    "key_frame_val": [25, -20],      "key_frame_num": [0, frame_end]}, 
    {"euler_xyz": [0,40,0],    "key_frame_val": [15, -20],      "key_frame_num": [0, frame_end]}, # !
    {"euler_xyz": [0,60,0],    "key_frame_val": [10, -15],      "key_frame_num": [0, frame_end]}, # !
    {"euler_xyz": [0,0,0],      "key_frame_val": [-20, 5, -20], "key_frame_num": [0, frame_mid, frame_end]}, 
    {"euler_xyz": [0,0,0],      "key_frame_val": [20, -5, 20], "key_frame_num": [0, frame_mid, frame_end]}, 
    {"euler_xyz": [0,-90,0],      "key_frame_val": [20, 5,  20], "key_frame_num": [0, frame_mid, frame_end]}, # ? 
    # {"euler_xyz": [0,0,0],      "key_frame_val": [-10, 20, -10], "key_frame_num": [0, frame_mid, frame_end]}, 
    # {"euler_xyz": [0,0,0], "key_frame_val": [-20, 20], "key_frame_num": [0, frame_end]}, 
]
class BaseTestScene(abc.ABC):
    """Base class for all test scenes.
    A test scene includes all relevant information to render a scene
    
    """
    def __init__(self, FLAGS, camera_path_config=None) -> None:
        self.simulator = None
        self.scene = None
        self.renderer = None
        self.rng = None
        self.flags = FLAGS
        self.output_dir = None
        self.scratch_dir = None
        self.background_hdri = None

        self.block_obj = None
        self.ref_h = 0
        self.add_table = False
        self.table_scale = 2
        self.shapenet_table_ids = None

        self.render_data = ("rgba",)
        self.background_hdri_id = FLAGS.background_hdri_id

        self.test_obj_states = {"violation": None, "non_violation": None}
        self.test_obj = None
        self.camera_look_at = [0,0,0]

        # load asset sources
        self.kubasic = kubasic_assets # kb.AssetSource.from_manifest(FLAGS.kubasic_assets)
        self.gso = gso_assets # kb.AssetSource.from_manifest(FLAGS.gso_assets)
        self.hdri_source = hdri_assets # kb.AssetSource.from_manifest(FLAGS.hdri_assets)

        # load background ids
        if os.path.exists("fy/configs/scene_asset_ids.txt"):
            with open("fy/configs/scene_asset_ids.txt", "r") as f:
                self.scene_asset_id_list = f.read().split("\n")
            logging.info(f"Loaded {len(self.scene_asset_id_list)} allowed scene asset ids from file.")
        else:
            self.scene_asset_id_list = self.hdri_source.all_asset_ids
        
        # load object ids
        if os.path.exists("fy/configs/gso_small_obj_ids.txt"):
            with open("fy/configs/gso_small_obj_ids.txt", "r") as f:
                self.small_object_asset_id_list = f.read().split("\n")
            logging.info(f"Loaded {len(self.small_object_asset_id_list)} allowed small object asset ids from file.")
            
        if os.path.exists("fy/configs/gso_big_obj_ids.txt"):
            with open("fy/configs/gso_big_obj_ids.txt", "r") as f:
                self.big_object_asset_id_list = f.read().split("\n")
            logging.info(f"Loaded {len(self.big_object_asset_id_list)} allowed big object asset ids from file.")

        if os.path.exists("fy/configs/gso_super_big_obj_ids.txt"):
            with open("fy/configs/gso_super_big_obj_ids.txt", "r") as f:
                self.super_big_object_asset_id_list = f.read().split("\n")
            logging.info(f"Loaded {len(self.super_big_object_asset_id_list)} allowed super big object asset ids from file.")

        if os.path.exists("fy/configs/gso_super_small_obj_ids.txt"):
            with open("fy/configs/gso_super_small_obj_ids.txt", "r") as f:
                self.super_small_object_asset_id_list = f.read().split("\n")
            logging.info(f"Loaded {len(self.super_small_object_asset_id_list)} allowed super small object asset ids from file.")
                
        if os.path.exists("fy/configs/gso_all_obj_asset_ids.txt"):
            with open("fy/configs/gso_all_obj_asset_ids.txt", "r") as f:
                all_gso_ids = f.read().split("\n")
                
            # assert small and big list are in all list
            for small_id in self.small_object_asset_id_list:
                assert small_id in all_gso_ids, f"{small_id} not in all list"
            for big_id in self.big_object_asset_id_list:
                assert big_id in all_gso_ids, f"{big_id} not in all list"
        
        if os.path.exists("fy/meshes/scenes"):
            with open("fy/configs/tables.txt", "r") as f:
                self.scenes = [os.path.join("fy/meshes/scenes", f) 
                               for f in os.listdir("fy/meshes/scenes")]

        if os.path.exists("fy/configs/tables.txt"):
            with open("fy/configs/tables.txt", "r") as f:
                self.shapenet_table_ids = f.read().split("\n")
          
        # load camera path config
        self.camera_path_config = path_template
        
        self.object_asset_id_list = self.gso.all_asset_ids
        
        for idx in range(len(self.camera_path_config)):
            self.camera_path_config[idx]["count"] = 0

        self.cur_camera_traj = None

        # self._setup_scene()
    
    # def create_lights(self,rng):
        
    #     sun = core.DirectionalLight(name="sun",
    #                                 color=color.Color.from_name("white"), shadow_softness=0.2,
    #                                 intensity=0.45, position=(11.6608, -6.62799, 25.8232))
    #     lamp_back = core.RectAreaLight(name="lamp_back",
    #                                     color=color.Color.from_name("white"), intensity=50.,
    #                                     position=(-1.1685, 2.64602, 5.81574))
    #     lamp_key = core.RectAreaLight(name="lamp_key",
    #                                     color=color.Color.from_hexint(0xffedd0), intensity=100,
    #                                     width=0.5, height=0.5, position=(6.44671, -2.90517, 4.2584))
    #     lamp_fill = core.RectAreaLight(name="lamp_fill",
    #                                     color=color.Color.from_hexint(0xc2d0ff), intensity=30,
    #                                     width=0.5, height=0.5, position=(-4.67112, -4.0136, 3.01122))
    #     lights = [sun, lamp_back, lamp_key, lamp_fill]

    #     # jitter lights
    #     for light in lights:
    #         light.position = light.position + rng.rand(3) 
    #         light.look_at((0, 5, 0))
        
    #     return lights
    def _setup_everything(self, shift=[0, 5, 0]):

        if random.random() <= self.flags.use_indoor_scene:
            self.add_table = True
            self._setup_indoor_scene()
        else:
            self.add_table = False
            self._setup_hdri_scene()
            self.ref_h = 0

        self._random_rotate_scene()

        if self.flags.debug:
            logging.info("Ignore background objects.")
        else:
            self.add_background_static_objects(3)
            self.add_background_dynamic_objects(1)

        self.add_block_objects()
        self.add_test_objects()

        
        
        # self.shift_scene(shift)
        if self.flags.move_camera:
            traj_idx = random.randint(0, len(self.camera_path_config)-1)
            self.cur_camera_traj = random.choice(self.camera_path_config)
            self._set_camera_path(self.cur_camera_traj)
            
        self._set_camera_focus_point([0, 0, self.ref_h]) # auto set the height to be the table height if exists

    def _set_camera_path(self, path_config):
        '''
        Set the camera's circular path
        '''

        center = [0, 0, 1.7] # TODO add this to config: path_config["center"]
        euler_xyz_deg = path_config["euler_xyz"]
        key_frame_idx = path_config["key_frame_num"]
        key_frame_val = path_config["key_frame_val"]
        
        camera = bpy.data.objects['camera']
        bpy.ops.curve.primitive_bezier_circle_add(enter_editmode=False, 
                                                align='WORLD', 
                                                location=center, 
                                                )
        circle = bpy.context.object
        euler_xyz = np.array(euler_xyz_deg) * np.pi / 180

        # scale and rotate the x and y axis of the circle
        for i in range(2):
            rot_ang_rad = euler_xyz[i] 

            # can't apply when angle = pi/2
            if np.isclose(np.abs(rot_ang_rad), np.pi/2):
                logging.warning("Singularity detected while scaling the circle")
                continue
            
            circle.scale[1-i] /=  np.cos(rot_ang_rad)
            circle.rotation_euler[i] = rot_ang_rad # rotation around y axis
            sin_prev = np.cos(rot_ang_rad)

        circle.rotation_euler[2] = euler_xyz[2]

        # set up camera constraint
        path_con = camera.constraints.new('FOLLOW_PATH')
        path_con.target = circle
        path_con.forward_axis = 'TRACK_NEGATIVE_Y'
        path_con.up_axis = 'UP_Z'
        path_con.use_curve_follow = True
        camera.location = (0, 0, 0)

        # setup camera keyframes
        for val, frame in zip(key_frame_val, key_frame_idx):
            path_con.offset = val
            path_con.keyframe_insert("offset", frame=frame)

        # set interpolation between keyframes
        action = camera.animation_data.action
        for fcurve in action.fcurves:
            if fcurve.data_path == "constraints[\"Follow Path\"].offset":
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = 'CUBIC'
                    keyframe.easing='EASE_IN_OUT'

        return path_con
    
    def _set_camera_focus_point(self, look_at=[0,0,0]):
        """Shift camera to look at a specific point

        Args:
            look_at (list, optional): _description_. Defaults to [0,0,0].
        """
        camera = bpy.data.objects['camera']

        # Create an Empty object at the target point
        bpy.ops.object.empty_add(location=look_at)
        focus_point = bpy.context.object

        # Add a "Track_To" constraint to the camera
        focus_con = camera.constraints.new(type='TRACK_TO')
        focus_con.target = focus_point
        focus_con.track_axis = 'TRACK_NEGATIVE_Z'
        focus_con.up_axis = 'UP_Y'

    def _random_rotate_scene(self):
        """Randomly rotate the scene and table (if has) 
        """
        # Generate a random angle between 0 and 2*pi
        angle = np.random.uniform(0, 2*np.pi)

        # Create a rotation matrix around the Z-axis
        rotation_matrix = Rotation.from_euler('z', angle).as_matrix()

        # Convert the rotation matrix to a NumPy array
        rotation_matrix_np = np.array(rotation_matrix)

        se3_tf = np.eye(4)
        se3_tf[:3, :3] = rotation_matrix_np
        
        for obj in bpy.data.objects:
            print(obj) if obj.name[0]=="V" or obj.name[0]=="T" else print("")
            matrix_world_old = obj.matrix_world.copy()
            if obj.name == "table":
                obj.rotation_mode = "XYZ"
                obj.rotation_euler[2] = angle
                break

            matrix_world_new = se3_tf @ matrix_world_old 

            for i in range(4):
                for j in range(4):
                    matrix_world_old[i][j] = matrix_world_new[i,j]

            # if obj.name == "table":
            #     obj.location[2] = -self.table_scale * self.table.aabbox[0][2] # matrix_world_old[2][3]
            #     print(-self.table_scale * self.table.aabbox[0][2], matrix_world_old)
            obj.matrix_world = matrix_world_old

    def prepare_scene(self):
        """Generate a new random test scene"""

        while True:
            self._setup_everything()
            if self._check_scene():
                self.generate_keyframes()
                return 
            
            if self.flags.move_camera:
                self.cur_camera_traj["count"] += 1

                if self.cur_camera_traj["count"] >= 20:
                    # remove the camera trajectory index
                    self.camera_path_config.pop(self.cur_camera_traj)
                    print(f"Removed camera trajectory {self.cur_camera_traj}")

    def _check_scene(self):
        """Check if the scene is valid. Return Flase if the scene is invalid.
        TODO: implement (Override) this function

        Returns:
            _type_: _description_
        """
        
        return True 
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        kb.done()

    def load_blender_scene(self, blender_scene):
        """Create empty scene and load blender scene

        Args:
            blender_scene (_type_): _description_
        """
        scene = core.scene.Scene.from_flags(self.flags)
        simulator = PyBullet(scene, self.scratch_dir)
        renderer = Blender(scene, self.scratch_dir,custom_scene=blender_scene)
        
        self.scene = scene
        self.simulator = simulator
        self.renderer = renderer
        
    def _setup_hdri_scene(self):
        """Setup the scene for rendering

        """
        # --- Common setups & resources
        scene, rng, output_dir, scratch_dir = kb.setup(self.flags)

        simulator = PyBullet(scene, scratch_dir)
        renderer = Blender(scene, scratch_dir)

        # --- Populate the scene
        # background HDRI
        all_backgrounds = self.scene_asset_id_list
        if self.background_hdri_id is not None:
            hdri_id = self.background_hdri_id
            logging.info(f"Using background {hdri_id} from {len(all_backgrounds)} background HDRI images")
        else:
            hdri_id = rng.choice(all_backgrounds)
            self.background_hdri_id = hdri_id
            logging.info(f"Choosing background {hdri_id} from {len(all_backgrounds)} background HDRI images")
        background_hdri = self.hdri_source.create(asset_id=hdri_id)
        assert isinstance(background_hdri, kb.Texture)
        scene.metadata["background"] = hdri_id
        renderer._set_ambient_light_hdri(background_hdri.filename)

        # Dome
        dome = self.kubasic.create(asset_id="dome", name="dome",
                                friction=1.0,
                                restitution=0.0,
                                static=True, background=True)
        assert isinstance(dome, kb.FileBasedObject)

        dome.friction = self.flags.floor_friction
        dome.restitution = self.flags.floor_restitution

        scene += dome
        dome_blender = dome.linked_objects[renderer]
        texture_node = dome_blender.data.materials[0].node_tree.nodes["Image Texture"]
        texture_node.image = bpy.data.images.load(background_hdri.filename)

        
        print("Setting up the Camera...")
        self._add_camera(scene)

        # each scene has a different camera setup, depending on the scene
        scene.camera.position = (0, -3, 1.7) # height 1.7, away 2m
        scene.camera.look_at((0, 0, 1))

        self.scene = scene
        self.simulator = simulator
        self.renderer = renderer
        self.rng = rng
        self.output_dir = output_dir
        self.scratch_dir = scratch_dir
        self.background_hdri = background_hdri

    def _add_camera(self, scene):
        scene.camera = kb.PerspectiveCamera(name="camera")

        # avoid name clash
        cam_name = "camera"
        set_name(cam_name)

    def _setup_indoor_scene(self, 
                            ):
        """Setup the indoor scene for rendering

        """
        # --- Common setups & resources
        scene, rng, output_dir, scratch_dir = kb.setup(self.flags)

        logging.info("Loading blender scene")
        blender_scene = rng.choice(self.scenes)
        self.load_blender_scene(blender_scene)
        self._add_camera(self.scene)
        

        # add floor to the scene
        logging.info("Adding floor to the scene")
        self._delete_from_blender_scene("floor")
        self.scene += kb.Cube(name="floor", scale=(10, 10, 0.001), position=(0, 0, -0.001),
                        static=True)
        
        floor_obj = bpy.context.object
        floor_obj.name = "floor"

        bpy.data.objects["floor"].hide_render = True
        bpy.data.objects["floor"].hide_viewport = True


        if self.add_table: 
            logging.info("Adding table to the scene")
            table = shapenet_assets.create(asset_id=rng.choice(self.shapenet_table_ids), static=True, name="table")
            # table_obj_id = self.shapenet_table_ids[0]#rng.choice(self.shapenet_table_ids)
            # table = self.add_object(assed_id=self.shapenet_table_ids[0], name="table")
            self.table = table
            table.metadata["is_dynamic"] = False
            table.scale = [self.table_scale] * 3
            table.quaternion = kb.Quaternion(axis=[1, 0, 0], degrees=90)
            table.position = table.position - (0, 0, table.aabbox[0][2])  
            table_h = table.aabbox[1][2] - table.aabbox[0][2]
            self.scene.add(table)
            set_name("table")
            self.ref_h = table_h
       
        self.rng = rng
        self.output_dir = output_dir
        self.scratch_dir = scratch_dir

        ################################
        # add random directional lighting
        # the light is placed at some random position sampled from a sphere, with min height
        ################################
        sphere_radius, min_height = 3, 2 # TODO^ adjust this
        h = self.rng.uniform(min_height, sphere_radius)
        r = np.sqrt(sphere_radius**2 - h**2)
        theta = self.rng.uniform(0, 2*np.pi)
        x, y = r * np.cos(theta), r * np.sin(theta)

        aim_at_range = (0, 0.5) # TODO^ adjust this 
        aim_at_r = self.rng.uniform(*aim_at_range)
        theta = self.rng.uniform(0, 2*np.pi)
        aim_at_x, aim_at_y = aim_at_r * np.cos(theta), aim_at_r * np.sin(theta)

        intensity_range = (10, 2000) # TODO^ adjust this
        intensity_val = self.rng.uniform(*intensity_range)

        shadow_soft_size = (0.05, 0.5)
        
        # add color with random color, strenth, 
        self.scene += kb.SpotLight(name="direc_light", position=(x, y, self.ref_h),
                        look_at=(aim_at_x, aim_at_y, self.ref_h), intensity=intensity_val)
        set_name("direc_light")

        direc_light = bpy.data.objects["direc_light"]
        direc_light.data.shadow_soft_size = self.rng.uniform(*shadow_soft_size)


    def shift_scene(self, shift: np.ndarray):
        """Shift the scene by a given vector.

        """
        for obj in self.scene.foreground_assets:
            obj.position = np.array(obj.position) + shift
        self.scene.camera.position = np.array(self.scene.camera.position) + shift
        
    # def add_static_object(self, n_obj:int = 1):
        
    #     logging.info("Randomly placing %d static objects:", n_obj)
    #     for i in range(n_obj):
    #         obj = self.gso.create(asset_id=self.rng.choice(self.object_asset_id_list))
    #         assert isinstance(obj, kb.FileBasedObject)
    #         scale = 2
    #         obj.scale = scale
    #         obj.metadata["scale"] = scale
    #         self.scene += obj
    #         kb.move_until_no_overlap(obj, self.simulator, spawn_region=STATIC_SPAWN_REGION,
    #                                 rng=self.rng)
    #         obj.friction = 1.0
    #         obj.restitution = 0.0
    #         obj.metadata["is_dynamic"] = False
    #         logging.info("    Added %s at %s", obj.asset_id, obj.position)

    #     logging.info("Running 100 frames of simulation to let static objects settle ...")
    #     _, _ = self.simulator.run(frame_start=-100, frame_end=0)

    def add_object(self, 
                   asset_id=None, 
                   position=None, 
                   quaternion=None,
                   velocity=(0,0,0), 
                   is_dynamic=True,
                   scale=2, 
                   **kwargs):
        """Add objects to the scene.

        
        """
        # delete the old object with the same name to avoid clashing
        if 'name' in kwargs:
            self._delete_from_blender_scene(kwargs['name'])
        # delete the object with the same input name
        if asset_id is not None:
            obj = self.gso.create(asset_id=asset_id, **kwargs)
        else:
            obj = self.gso.create(asset_id=self.rng.choice(self.object_asset_id_list), **kwargs)

        assert isinstance(obj, kb.FileBasedObject)


        obj.velocity = velocity
        obj.scale = scale
        obj.metadata["scale"] = scale

        if quaternion is not None:
            obj.quaternion = quaternion
        else:
            self.set_random_rotation(obj)

        self.scene += obj

        # find the object by name in bpy.data.objects
        if 'name' in kwargs:
            name = kwargs['name']
            set_name(name)

        if position is not None:
            obj.position = position
        else:
            kb.move_until_no_overlap(obj, self.simulator, spawn_region=STATIC_SPAWN_REGION,
                                    rng=self.rng)

        if is_dynamic: # temporarily set false
            # reduce the restitution of the object to make it less bouncy
            # account for the gravity
            restituion_scale = -self.gravity[2] / 9.8
            obj.restitution *= restituion_scale
        else:
            # make the object static
            obj.friction = 1.0
            obj.restitution = 0.0
        
        obj.static = not is_dynamic
        obj.metadata["is_dynamic"] = is_dynamic

        logging.info("    Added %s at %s", obj.asset_id, obj.position)

        return obj

    def _delete_from_blender_scene(self, name):
        obj_del = bpy.context.scene.objects.get(name)
        if obj_del:
            bpy.data.objects.remove(obj_del, do_unlink = True)
            logging.info(f"The existing object '{name}' will be replaced")

    def _run_simulate(self, save_state=False):
        """Run simulation and write to keyframes of objects

        Args:
            save_state (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        animation, collisions = self.simulator.run(frame_start=0,
                                      frame_end=self.scene.frame_end+1)
        
        if save_state:
            fname = f"{self.background_hdri_id}.blend"
            full_path = self.output_dir / fname
            logging.info("Saving the renderer state to '%s' ",
                        full_path)
            self.renderer.save_state(full_path)

        return animation, collisions

    def render(self, save_to_file=False, **kwargs):
        """Render the scene and save to file

        Args:
            save_to_file (bool, optional): _description_. Defaults to False.

        Returns:
            _type_: _description_
        """
        data_stack = self.renderer.render(return_layers=self.render_data)

        if save_to_file:
            kb.write_image_dict(data_stack, self.output_dir, **kwargs)

        return data_stack
        
    def write_metadata(self):
        logging.info("Collecting and storing metadata for each object.")
        # return
        kb.write_json(filename=self.output_dir / "metadata.json", data={
            "flags": vars(self.flags),
            "metadata": kb.get_scene_metadata(self.scene),
            # "camera": kb.get_camera_info(self.scene.camera),
            "instances": kb.get_instance_info(self.scene),
        })

    def change_output_dir(self, new_output_dir):
        if isinstance(new_output_dir, str):
            new_output_dir = epath.Path(new_output_dir)
        elif isinstance(new_output_dir, epath.Path):
            pass
        else:
            raise ValueError("new_output_dir must be a string or epath.Path")

        self.output_dir = new_output_dir
        logging.info("Output directory changed to %s", self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def add_background_static_objects(self, n_obj:int = 1):
        """Add some static objects as background objects

        """
        for _ in range(n_obj):
            self.add_object(is_dynamic=False)
            
        logging.info("Running 100 frames of simulation to let static objects settle ...")
        _, _ = self.simulator.run(frame_start=-100, frame_end=0)

    def add_background_dynamic_objects(self, 
                                       n_obj:int = 1, 
                                       scale: float = 2,
                                       x_range: tuple = (-3, 3), 
                                       y_range: tuple = (0.5, 1.5), 
                                       z_range: tuple = (3, 5)):
        """Add some other dynamic objects as background objects
        
        """
        for _ in range(n_obj):
            # make random free fall
            rand_pos = self.rng.uniform(-1, 1, 3)
            
            for i, u in enumerate([x_range, y_range, z_range]):
                mean = (u[1] + u[0]) / 2
                scale = (u[1] - u[0]) / 2
                rand_pos[i] = rand_pos[i] * scale + mean 

            rand_vel = self.rng.uniform(-3, 3, 3)
            sign = -1 if rand_pos[0] < 0 else 1
            rand_vel[0] = -sign * abs(rand_vel[0]) # make the object move towards the center
            self.add_object(position=rand_pos,
                            velocity=rand_vel,
                            is_dynamic=True,
                            scale=scale)

    @abc.abstractmethod
    def add_test_objects(self):
        pass

    # @abc.abstractmethod
    def add_block_objects(self):
        """_summary_
        TODO!!!: MAKE SURE the object is properly oriented so that it blocks the test object
        TODO^: Write a utility function to check the object's principal axis
        SHOULD be randomly placed (not implemented).
        Move to the table after rotation (not implemented)
        """
        block_obj_id = self.rng.choice(self.super_big_object_asset_id_list)
        self.block_obj = self.add_object(asset_id=block_obj_id,
                                position=(0, 0, 0),
                                quaternion=(1,0,0,0),
                                is_dynamic=True,
                                scale=1.25, 
                                name="block"
                                )

        aligh_block_objs(self.block_obj)

        self.block_obj.position = (0, 0, self.ref_h - self.block_obj.aabbox[0][2])

        # randomly jitter the object
        ...

    @abc.abstractmethod
    def generate_keyframes(self):
        pass
        

    ############################
    # helper functions
    ############################
    def set_random_rotation(self, obj):
        """Set a random rotation for the object.

        """
        def mul_2pi(x):
            return x * 2 * np.pi
        u, v, w = self.rng.uniform(0, 1, 3)
        obj.quaternion = ( np.sqrt(1-u) * np.sin(mul_2pi(v)), \
            np.sqrt(1-u) * np.cos(mul_2pi(v)), \
            np.sqrt(u) *  np.sin(mul_2pi(w)), \
            np.sqrt(u) * np.cos(mul_2pi(w)) )
    @staticmethod
    def get_object_state_at_frame(obj, frame):
        """Get the state of the object at a given frame

        Args:
            obj (_type_): object
            frame (_type_): frame number 

        Returns:
            _type_: _description_
        """
        state = {}
        for prop in ["position", "velocity", "quaternion", "angular_velocity"]:
            state[prop] = obj.get_value_at(prop, frame)
        return state
    
    @staticmethod
    def set_object_state(obj, state):
        """Set the current state of the object

        Args:
            obj (_type_): _description_
            state (_type_): _description_
        """
        for prop in state:
            setattr(obj, prop, state[prop])

    def get_object_keyframes(self, obj):
        """Get all keyframes for the object
        Args:
            obj (_type_): _description_

        Returns:
            _type_: _description_
        """
        save_properties = ["position", "velocity", "quaternion", "angular_velocity"]
        state = {}
        for prop in save_properties:
            for frame in range(self.scene.frame_end+1):
                if prop not in state:
                    state[prop] = {}
                state[prop][frame] = obj.keyframes[prop][frame].copy()
                    
        return state
        
    def set_object_keyframes(self, obj, state):
        """Set keyframes for the object

        Args:
            obj (_type_): _description_
            state (_type_): _description_
        """
        for prop in state:
            for frame in range(self.scene.frame_end+1):
                setattr(obj, prop, state[prop][frame])
                obj.keyframe_insert(prop, frame)

    def set_test_objects_static(self):
        for obj in self.test_obj:
            obj.static = True
            
    def set_test_objects_dynamic(self):
        for obj in self.test_obj:
            obj.static = False
        
    def save_violation_scene(self):
        states = []
        for obj in self.test_obj:
            state = self.get_object_keyframes(obj)
            states.append(state)
        self.test_obj_states["violation"] = states
    
    def load_violation_scene(self):
        for i, obj in enumerate(self.test_obj):
            self.set_object_keyframes(obj, self.test_obj_states["violation"][i])
        
    def save_non_violation_scene(self):
        states = []
        for obj in self.test_obj:
            state = self.get_object_keyframes(obj)
            states.append(state)
        self.test_obj_states["non_violation"] = states
        
    def load_non_violation_scene(self):
        for i, obj in enumerate(self.test_obj):
            self.set_object_keyframes(obj, self.test_obj_states["non_violation"][i])
        


                                    