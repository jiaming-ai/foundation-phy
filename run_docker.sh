

docker run --rm -it \
  --user 1000:1000 \
  --volume "$PWD:/workspace" \
  --workdir "/workspace" \
  kubricdockerhub/kubruntudev:latest \
  /bin/bash