


from fy.utils import get_args
from fy.collision import CollisionTestScene
import logging
from fy.base import BaseTestScene
import kubric as kb
import imageio
from fy.utils import write_video
from fy.solidity import SolidityTestScene

from etils import epath

def main() -> None:
    FLAGS = get_args()
    logging.basicConfig(level=FLAGS.logging_level)

    num_per_cls = 50
    max_trails = 1
    test_cls_all = {
        "solidity": SolidityTestScene,
        # "collision": CollisionTestScene
    }
    for test_name, test_cls in test_cls_all.items():
        n = 0
        for i in range(max_trails):
            logging.info(f"========== Rendering {test_name} test {n} ===========")
            output_dir = f"output/{test_name}/scene_{n}/"
            FLAGS.job_dir = output_dir
            try:
                generate_test_scene(test_cls, FLAGS, output_dir)
                n += 1
                if n >= num_per_cls:
                    break
            except Exception as e:
                logging.error(f"Error rendering collision test {n}: {e}\n Skipping to the next one.")
                # if debug is on, raise the exception
                if FLAGS.debug:
                    raise
                continue


def generate_test_scene(test_class, FLAGS,output_dir) -> None:

    with test_class(FLAGS) as test_scene:
        # first prepare the scene
        logging.info("Preparing the scene")
        test_scene.prepare_scene()
        test_scene.write_metadata()

        # render the violation state
        test_scene.change_output_dir( output_dir + "violation" )

        # igore rendering if debug is on
        if not FLAGS.debug:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "violation/", output_dir + "violation.mp4")

        # load the non-violation state and render it
        logging.info("Loading the non-violation state")
        test_scene.load_non_violation_scene()
        test_scene.change_output_dir( output_dir + "non_violation" )
        logging.info("Rendering the non-violation state")

        # igore rendering if debug is on
        if not FLAGS.debug:
            test_scene.render(save_to_file=True)
            write_video(output_dir + "non_violation/", output_dir + "non_violation.mp4")

if __name__ == "__main__":
    main()
    