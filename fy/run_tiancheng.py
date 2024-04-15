


from fy.utils import get_args
import logging
import kubric as kb
import imageio
from fy.utils import write_video
from fy.solidity import SolidityTestScene
from fy.collision import CollisionTestScene
from fy.permanance import PermananceTestScene
from fy.continuity import ContinuityTestScene
from fy.support import SupportTestScene
from tqdm import tqdm
import colorlog
import os

from etils import epath
from random import choice
print(flush=True)
## TODO: set frame num from arg
frame_mid = 18
frame_end = 36
output_dirname = "render_output"
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

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("output/log"),
            # logging.StreamHandler()
        ]
    )


    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
    "%(log_color)s %(asctime)s %(levelname)s:%(message)s",
    log_colors={
        'DEBUG': 'white',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red',
    }
    ))

    logger = logging.getLogger()
    logger.addHandler(handler)

    
    num_per_cls = 50
    max_trails = 40 if not(FLAGS.debug) else 10
    test_cls_all = {
        # "solidity": SolidityTestScene,
        "continuity": ContinuityTestScene, 
        "Support": SupportTestScene, 
        # "collision": CollisionTestScene
        # "Permanance": PermananceTestScene 
    }
    for test_name, test_cls in test_cls_all.items():
        n = 0
        for i in tqdm(range(max_trails)):
            output_dir = f"{output_dirname}/{test_name}/scene_{i}/"
            if os.path.isdir(output_dir):
                if any([True for _ in os.listdir(output_dir)]):
                    logging.warning(f"Directory {output_dir} already exists, skip rendering the current scene")
                    continue 

            print(f"========== Rendering {test_name} test {i} ===========")
            video_dir = f"{output_dirname}/{test_name}/videos/"
            FLAGS.job_dir = output_dir
            # FLAGS.camera_path_config = choice(path_template)

            if test_name in ["Support", "continuity"]:
                FLAGS.move_camera = False

            generate_test_scene(test_cls, FLAGS, output_dir, video_dir, i)
            n += 1
            # if n >= num_per_cls:
            #     break
            


def generate_test_scene(test_class, FLAGS, output_dir, video_dir, i) -> None:
    if not(os.path.exists(video_dir)):
        os.makedirs(video_dir)
    with test_class(FLAGS) as test_scene:
        # first prepare the scene
        print("Preparing the scene")
        test_scene.prepare_scene()
        test_scene.write_metadata()

        # render the violation state
        test_scene.change_output_dir( output_dir + "violation" )

        print("Rendering the violation state")
        # igore rendering if debug is on
        if not FLAGS.debug:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "violation/", video_dir + f"violation_{i}.mp4")

        # load the non-violation state and render it
        print("Loading the non-violation state")
        test_scene.load_non_violation_scene()
        test_scene.change_output_dir( output_dir + "non_violation" )
        print("Rendering the non-violation state")

        # igore rendering if debug is on
        if not FLAGS.debug:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "non_violation/", video_dir + f"non_violation_{i}.mp4")
        
if __name__ == "__main__":
    main()
    