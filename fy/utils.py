
import kubric as kb
import imageio
import bpy
import numpy as np 
from tqdm import tqdm
from random import sample
from distutils.util import strtobool

txt2bool = lambda x:bool(strtobool(x))

def get_args():

  # --- CLI arguments
  parser = kb.ArgumentParser()

  # Configuration for the floor and background
  parser.add_argument("--floor_friction", type=float, default=0.3)
  parser.add_argument("--floor_restitution", type=float, default=0.5)
  parser.add_argument("--backgrounds_split", choices=["train", "test"],
                      default="train")

  parser.add_argument("--background_hdri_id", type=str, default=None,
                      help="ID of the HDRI background to use. If not given, a random one is chosen")


  # Configuration for the source of the assets
  parser.add_argument("--kubasic_assets", type=str,
                      default="gs://kubric-public/assets/KuBasic/KuBasic.json")
  parser.add_argument("--hdri_assets", type=str,
                      default="gs://kubric-public/assets/HDRI_haven/HDRI_haven.json")
  parser.add_argument("--gso_assets", type=str,
                      default="gs://kubric-public/assets/GSO/GSO.json")
  parser.add_argument("--save_state", dest="save_state", action="store_true")

  # 3s of animation at 12 fps
  parser.set_defaults(save_state=False, frame_end=36, frame_rate=12,
                      resolution="512x512")
  
  parser.add_argument("--debug", type=txt2bool, default=False)
  
  parser.add_argument("--generate_violation", type=txt2bool, default=True) # generate violation results
  parser.add_argument("--save_states", type=txt2bool, default=False) # save states
  parser.add_argument("--render_both_results", type=txt2bool, default=True) # render both violation and non-violation results
  
  FLAGS = parser.parse_args()

  if FLAGS.debug:
    FLAGS.logging_level = "DEBUG"
    FLAGS.save_states = True
    print("Debug mode is on")
    
  return FLAGS

def write_video(source_dir, output_file):
  # read png files
  images = []
  for i in range(1, 36):
      filename = f"{source_dir}/rgba_{i:05d}.png"
      images.append(imageio.imread(filename))
      
  # write to mpeg video
  # imageio.mimsave('output/movie.gif', images, fps=12)
  imageio.mimsave(output_file, images, fps=12)

# def set_gpu_render():
#   # for scene in bpy.data.scenes:
#   #   bpy.context.scene.render.engine = 'CYCLES' 
#   #   bpy.data.scenes["Scene"].cycles.device='GPU' 
#   #   bpy.context.scene.cycles.device = 'GPU'

#   # bpy.context.preferences.addons['cycles'].preferences.compute_device_type = "CUDA"
#   # bpy.context.preferences.addons['cycles'].preferences.devices[1].use = True

#   # https://blender.stackexchange.com/questions/104651/selecting-gpu-with-python-script
#   bpy.data.scenes[0].render.engine = "CYCLES"
#   bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "CUDA" # or "OPENCL"

#   # Set the device and feature set
#   bpy.context.scene.cycles.device = "GPU"

#   # get_devices() to let Blender detects GPU device
#   # print(bpy.context.preferences.addons["cycles"].preferences.get_devices())
#   # print(bpy.context.preferences.addons["cycles"].preferences.compute_device_type)
#   for d in bpy.context.preferences.addons["cycles"].preferences.devices:
#       d["use"] = 1 # Using all devices, include GPU and CPU
#       print(d["name"], d["use"])

def set_camera_path_constraint_circular(
                              center=(0, 0, 1.7),
                              radius=1.5, 
                              euler_xyz_deg=[-20, -40*0, 0]):
  '''
  Constrain the camera 
  '''
  camera = bpy.data.objects['Camera']
  bpy.ops.curve.primitive_bezier_circle_add(enter_editmode=False, 
                                          align='WORLD', 
                                          location=center, 
                                          )
  circle = bpy.context.object
  euler_xyz = np.array(euler_xyz_deg) * np.pi / 180

  # scale and rotate x and y
  for i in range(2):
    rot_ang_rad = euler_xyz[i] 

    # can't apply when angle = pi/2
    if np.isclose(np.abs(rot_ang_rad), np.pi/2):
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

  return path_con

def set_camera_path_constraint_linear(position=(0, 0, 1.7), 
                                      rot_ang_deg=45):
  camera = bpy.data.objects['Camera']
  bpy.ops.curve.primitive_nurbs_path_add(enter_editmode=False, 
                                                align='WORLD', 
                                                location=position, 
                                                scale=(1, 1, 1))
  linear_path = bpy.context.object
  linear_path.rotation_euler[2] = 45

  path_con = camera.constraints.new('FOLLOW_PATH')
  path_con.target = linear_path
  path_con.forward_axis = 'TRACK_NEGATIVE_Y'
  path_con.up_axis = 'UP_Z'
  path_con.use_curve_follow = True
  camera.location = (0,0,0)

  return path_con

def set_camera_orn_constraint(position=(0, 0, 0)):
  '''
  Constraint the camera to always look at a fixed point
  '''
  camera = bpy.data.objects['Camera']

  # Create an Empty object at the origin
  bpy.ops.object.empty_add(location=position)
  focus_point = bpy.context.object

  # Add a Track To constraint to the camera
  focus_con = camera.constraints.new(type='TRACK_TO')
  focus_con.target = focus_point
  focus_con.track_axis = 'TRACK_NEGATIVE_Z'
  focus_con.up_axis = 'UP_Y'

  return focus_con

def set_camera_keyframes(vals=[-20, 20], frames=[0, 72], interpolation='CUBIC'):
        path_con = bpy.data.objects['Camera'].constraints['Follow Path']
        camera = bpy.data.objects['Camera']  

        for val, frame in zip(vals, frames):
            path_con.offset = val
            path_con.keyframe_insert("offset", frame=frame)

        # --- set keyframe interpolation
        action = camera.animation_data.action
        for fcurve in action.fcurves:
            if fcurve.data_path == "constraints[\"Follow Path\"].offset":
                for keyframe in fcurve.keyframe_points:
                    keyframe.interpolation = interpolation
                    keyframe.easing='EASE_IN_OUT'

def set_object_disappear(name, frame):
  obj = bpy.data.objects[name]
  
  obj.keyframe_insert("location", frame=1)
  
  obj.location[2] = -10
  obj.keyframe_insert("location", frame=frame)

  # --- set keyframe interpolation
  action = obj.animation_data.action

  for fcurve in action.fcurves:
      if fcurve.data_path == "location":
          for keyframe in fcurve.keyframe_points:
              keyframe.interpolation = "CONSTANT"

                    

def getVisibleVertexFraction(obj_name, rng, sample_num=1000):
    """
    Calculates and returns the fraction of vertices of a given object that are visible from a given camera position.

    This function works by casting rays from the camera to each vertex of the object. 
    If a ray intersects with another object before it reaches the vertex, 
    the vertex is considered occluded. The function then calculates the 
    fraction of vertices that are not occluded.

    Params:
    - camera (bpy.types.Object): The camera object from which visibility is checked.
    - obj (bpy.types.Object): The object whose vertices' visibility is to be checked.

    Returns:
    - float: The fraction of vertices of the object that are visible from the camera position.
    """
    camera = bpy.data.objects['Camera']
    obj = bpy.data.objects[obj_name]
    
    camera_loc = [camera.matrix_world[0][3], camera.matrix_world[1][3], camera.matrix_world[2][3]]
    num_vert = len(obj.data.vertices)
    num_vert_in_fov = 0 # number of vertices in the camera's field of view

    vert_list = list(obj.data.vertices)
    sampled_verts = sample(vert_list, sample_num) if sample_num < len(vert_list) else vert_list
    sample_num = len(sampled_verts)
    for vert in sampled_verts:
        vert_loc = obj.matrix_world @ vert.co
        dist = np.array(vert_loc) - np.array(camera_loc)
        dist = dist / np.linalg.norm(dist)

        # apply ray casting to check whether the object is blocked in view
        result, location, normal, index, target, matrix = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, camera_loc, dist)
        if target is not None:
          num_vert_in_fov += (target.name == obj.name)

    return num_vert_in_fov / sample_num


# def a(sample_num=1000):
#     rng = np.random.RandomState()
#     camera = bpy.data.objects['Camera']
#     obj = bpy.data.objects["small_obj"]
#     camera_loc = [camera.matrix_world[0][3], camera.matrix_world[1][3], camera.matrix_world[2][3]]
#     num_vert = len(obj.data.vertices)
#     num_vert_in_fov = 0 # number of vertices in the camera's field of view
#     for vert in (obj.data.vertices):
#         vert_loc = obj.matrix_world @ vert.co
#         dist = np.array(vert_loc) - np.array(camera_loc)
#         dist = dist / np.linalg.norm(dist)
#         # apply ray casting to check whether the object is blocked in view
#         result, location, normal, index, target, matrix = bpy.context.scene.ray_cast(bpy.context.view_layer.depsgraph, camera_loc, dist)
#         num_vert_in_fov += (target.name == obj.name)
#     return num_vert_in_fov / num_vert
