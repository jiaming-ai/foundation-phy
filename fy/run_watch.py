""" Run the script as subprocess, restart it if it is killed by the system. """
import os
import subprocess
import argparse
import time
def check_if_job_finished(num_per_cls: int, test_scene_cls) -> bool:
    # check if output/{test_scene} has {num_per_cls} folders
    for test_scene in test_scene_cls:
        scene_output_dir = f"output/{test_scene}"
        # print(scene_output_dir)
        # print(os.getcwd())
        # print(os.path.exists('output'))
        if os.path.exists(scene_output_dir):
            n = len(os.listdir(scene_output_dir))
            if n >= num_per_cls:
                print(f"Found {n} rendered test in the {scene_output_dir} folder. Job finished for {test_scene}.")
                continue
        print(f"Job not finished. Found {n} rendered test in the {scene_output_dir} folder.")
        return False
    return True

def run_watch():
    parser = argparse.ArgumentParser()
    parser.add_argument("--num_per_cls", type=int, required=True)
    parser.add_argument("--test_scene_cls",nargs='+', required=True) # test scenes
    # rest of the arguments as list
    
    args, other_args = parser.parse_known_args()
    print(args)
    print(other_args)

    while True:
        # check if the job is finished
        
        if check_if_job_finished(args.num_per_cls, args.test_scene_cls):
            print("Job finished.")
            break

        all_args = ["/bin/python", "fy/run.py", "--num_per_cls", str(args.num_per_cls), "--test_scene_cls"] + args.test_scene_cls + other_args
        print("=============================================================")
        print("Restarting the job with the following arguments:")
        print(" ".join(all_args))
        print("=============================================================")
        proc = subprocess.Popen(all_args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)

        while True:
            # first check if the job is killed
            if proc.poll() is not None:
                print("Job is killed. Restarting the job.")
                break
            # read all the output since the last read
            output = proc.stdout.read(200)

            if output == b'' and proc.poll() is not None:
                break
            if output:
                print(output.strip().decode())
            # print("Still runing...")
            # wait for 1 second
            time.sleep(1)

    
if __name__ == "__main__":
    run_watch()