

docker run --rm -it \
  --user 1000:1000 \
  --volume "$PWD:/workspace" \
  --volume "/data/llm_physics/fy_data/tmp:/tmp" \
  --volume "/data/llm_physics/fy_data:/data/llm_physics/fy_data" \
  --workdir "/workspace" \
  --gpus all \
  --env KUBRIC_USE_GPU=1 \
  kubricdockerhub/kubruntudev:latest \
  /bin/bash