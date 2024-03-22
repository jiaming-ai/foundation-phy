from fy.utils import get_args
import logging
import kubric as kb
import imageio
from fy.utils import write_video
from fy.continuity import ContinuityTestScene, path_template

from etils import epath

def main() -> None:
    FLAGS = get_args()
    logging.basicConfig(level=FLAGS.logging_level)

    num_test = 1
    for i, params in enumerate(path_template):
        logging.info(f"========== Rendering collision test {i} ===========")
        output_dir = f"output_egocentric/continuity_{i}/"
        FLAGS.job_dir = output_dir
        generate_continuity_test(FLAGS, params, output_dir)
        # break
        # try:
        #     generate_continuity_test(FLAGS, output_dir)
        # except Exception as e:
        #     logging.error(f"Error rendering collision test {i}: {e}")
        #     continue



def generate_continuity_test(FLAGS, path, output_dir) -> None:

    with ContinuityTestScene(FLAGS, path) as cont_scene:
        # first prepare the scene
        # both violation and non-violation states are saved
        logging.info("Preparing the scene")
        # cont_scene.load_blender_scene("meshes/scenes/game-room-scaled.blend")
        # collision_scene.write_metadata()

        # # render the violation state
        cont_scene.change_output_dir( output_dir + "noviolation" )
        cont_scene.prepare_scene(shift=[0,0,0])
        cont_scene.renderer.save_state( output_dir + "empty.blend")

        # collision_scene.render(save_to_file=True)
        # write_video(output_dir + "violation/", output_dir + "violation.mp4")

        # # load the non-violation state and render it
        # logging.info("Loading the non-violation state")
        # collision_scene.load_test_obj_state("non_violation")
        # collision_scene.change_output_dir( output_dir + "non_violation" )
        # logging.info("Rendering the non-violation state")
        # collision_scene.render(save_to_file=True)
        # write_video(output_dir + "non_violation/", output_dir + "non_violation.mp4")

# def test_all_scenes() -> None:
#     logging.basicConfig(level=logging.DEBUG)
#     FLAGS = get_args()
#     # FLAGS.frame_end = 1

#     hdri_source = kb.AssetSource.from_manifest(FLAGS.hdri_assets)
#     scene_asset_id_list = hdri_source.all_asset_ids

#     # # write the scene asset ids to a file
#     # with open("output/scene_asset_ids.txt", "w") as f:
#     #     f.write("\n".join(scene_asset_id_list))
    
#     for scene_asset_id in scene_asset_id_list:
#         FLAGS.background_hdri_id = scene_asset_id
#         print(f"Rendering scene {scene_asset_id}")
#         with ShowScene(FLAGS) as scene:
#             scene.add_objects()
#             scene.run_simulate(True)


# def test_video():
#     # read png files
#     images = []
#     for i in range(1, 36):
#         filename = f"output/rgba_{i:05d}.png"
#         images.append(imageio.imread(filename))
        
#     # write to mpeg video
#     # imageio.mimsave('output/movie.gif', images, fps=12)
#     imageio.mimsave('output/movie.mp4', images, fps=12)
    
        
if __name__ == "__main__":
    main()
    
    # test_video()
