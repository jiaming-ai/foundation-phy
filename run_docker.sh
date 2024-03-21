

docker run --rm -it \
  --user 1000:1000 \
  --volume "$PWD:/workspace" \
  --workdir "/workspace" \
  --gpus all \
  --env KUBRIC_USE_GPU=1 \
  kubricdockerhub/kubruntudev:latest \
  /bin/bash