# Foundation Physics


## Running in development environment

```bash

git clone https://github.com/jiaming-robot-learning/foundation-phy.git
cd foundation-phy
docker pull kubricdockerhub/kubruntudev:latest

# optional: if you want to build the image from scratch
cd kubric
docker build -f docker/Blender.Dockerfile -t kubricdockerhub/blender:latest .  # build a blender image first
docker build -f docker/KubruntuDev.Dockerfile -t kubricdockerhub/kubruntudev:latest .  # then build a kubric image of which base image is the blender image above

docker run --rm -it \
  --user 1000:1000 \
  --volume "$PWD:/workspace" \
  --workdir "/workspace" \
  kubricdockerhub/kubruntudev:latest \
  /bin/bash

```
