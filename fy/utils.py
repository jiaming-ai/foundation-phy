
import kubric as kb
import imageio


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
  
  parser.add_argument("--debug", type=bool, default=False)
  
  parser.add_argument("--generate_violation", type=bool, default=True) # generate violation results
  parser.add_argument("--save_states", type=bool, default=False) # save states
  parser.add_argument("--render_both_results", type=bool, default=True) # render both violation and non-violation results
  
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