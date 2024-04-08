


from fy.utils import get_args
import logging
import kubric as kb
import imageio
from fy.utils import write_video
from fy.solidity import SolidityTestScene
from fy.collision import CollisionTestScene
from fy.permanance import PermananceTestScene

from etils import epath
from random import choice

## TODO: set frame num from arg
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

def main() -> None:
    FLAGS = get_args()
    logging.basicConfig(level=FLAGS.logging_level)

    num_per_cls = 50
    max_trails = 1
    test_cls_all = {
        # "solidity": SolidityTestScene,
        # "collision": CollisionTestScene
        "Permanance": PermananceTestScene 
    }
    for test_name, test_cls in test_cls_all.items():
        n = 0
        for i in range(max_trails):
            print(f"========== Rendering {test_name} test {n} ===========")
            output_dir = f"output_temp/{test_name}/scene_{n}/"
            FLAGS.job_dir = output_dir
            FLAGS.camera_path_config = choice(path_template)

            generate_test_scene(test_cls, FLAGS, output_dir)
            n += 1
            if n >= num_per_cls:
                break
            


def generate_test_scene(test_class, FLAGS,output_dir=None) -> None:

    with test_class(FLAGS) as test_scene:
        # first prepare the scene
        print("Preparing the scene")
        test_scene.prepare_scene()
        test_scene.write_metadata()

        # render the violation state
        test_scene.change_output_dir( output_dir + "violation" )

        print("Rendering the violation state")
        # igore rendering if debug is on
        if not FLAGS.debug and False:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "violation/", output_dir + "violation.mp4")

        # load the non-violation state and render it
        print("Loading the non-violation state")
        test_scene.load_non_violation_scene()
        test_scene.change_output_dir( output_dir + "non_violation" )
        print("Rendering the non-violation state")

        # igore rendering if debug is on
        if not FLAGS.debug and False:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "non_violation/", output_dir + "non_violation.mp4")
        
if __name__ == "__main__":
    main()
    