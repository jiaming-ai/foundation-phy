


import logging
import colorlog
from fy.utils import get_args
import kubric as kb
from fy.utils import write_video

from fy.solidity import SolidityTestScene
from fy.collision import CollisionTestScene
from fy.permanance import PermananceTestScene
from fy.continuity import ContinuityTestScene
from fy.support import SupportTestScene
import os
import time
from fy.collision_free_fall import CollisionScene

def main() -> None:
    FLAGS = get_args()

    logging.basicConfig(level=FLAGS.logging_level)
    output_dirname = "render_output" if not(FLAGS.save_states) else "output_temp"

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"{output_dirname}/log"),
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

    num_per_cls = 1000
    max_trails = 5000
    test_cls_all = {
        # "solidity": SolidityTestScene,
        # "collision": CollisionTestScene,
        # "collision_free_fall": CollisionScene,
        # "Permanance": PermananceTestScene ,
        "Continuity": ContinuityTestScene,
        # "Support": SupportTestScene,

    }
    for test_name, test_cls in test_cls_all.items():
        # check if exist rendered test in the output folder
        # if exist, start from the last one
        scene_output_dir = f"{output_dirname}/{test_name}/"
        # if os.path.exists(scene_output_dir):
        #     n = len(os.listdir(scene_output_dir))
        #     logging.info(f"Found {n} rendered test in the output folder. Start from the next one.")
        # else:
        #     n = 0
        n = 0

        for i in range(max_trails):
            
            logging.info(f"========== Rendering {test_name} test {n} ===========")
            output_dir = f"{output_dirname}/{test_name}/scene_{n}/"

            while True:
                if os.path.isdir(output_dir):
                    # if any([True for _ in os.listdir(output_dir)]):
                    if os.path.isfile(os.path.join(output_dir, "metadata.json")):
                        logging.warning(f"Directory {output_dir} already exists, skip rendering the current scene")
                        n += 1 
                        output_dir = f"{output_dirname}/{test_name}/scene_{n}/"
                        continue
                break

            FLAGS.job_dir = output_dir
            try:
                generate_test_scene(test_cls, FLAGS, output_dir, n)
                n += 1
                if n >= num_per_cls:
                    break
            except Exception as e:
                logging.error(f"Error rendering {test_name} test {n}: {e}\n Skipping to the next one.")
                # if debug is on, raise the exception
                if FLAGS.debug:
                    raise
                continue

def generate_test_scene(test_class, FLAGS,output_dir, i) -> None:
    video_dir = os.path.join(output_dir.rsplit('/', 2)[0], "videos/")
    if not(os.path.exists(video_dir)):
        os.makedirs(video_dir)
    # print(video_dir); return

    with test_class(FLAGS) as test_scene:
        # first prepare the scene
        logging.info("Preparing the scene")
        test_scene.prepare_scene()
        test_scene.write_metadata()

        # render the violation state
        test_scene.change_output_dir( output_dir + "violation" )

        if FLAGS.render_violate_video:
            logging.info("Rendering the violation video")
            start_time = time.time()
            test_scene.render(save_to_file=True)
            # write_video(output_dir + "violation/", output_dir + "violation.mp4")
            logging.info(f"Rendering the violation video took {time.time() - start_time} seconds")

        # load the non-violation state and render it
        logging.info("Loading the non-violation state")
        test_scene.load_non_violation_scene()
        test_scene.change_output_dir( output_dir + "non_violation" )

        # igore rendering if debug is on
        if FLAGS.render_non_violate_video:
            logging.info("Rendering the non-violation video")
            start_time = time.time()
            test_scene.render(save_to_file=True)
            write_video(output_dir + "non_violation/", video_dir + f"non_violation_{i}.mp4")
            logging.info(f"Rendering the non-violation video took {time.time() - start_time} seconds")

if __name__ == "__main__":
    main()
    
    