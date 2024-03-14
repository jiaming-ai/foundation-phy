# Foundation Physics


## Running in development environment

```bash

git clone https://github.com/jiaming-robot-learning/foundation-phy.git
cd foundation-phy
docker pull kubricdockerhub/kubruntudev:latest

docker run --rm -it \
  --user 1000:1000 \
  --volume "$PWD:/workspace" \
  --workdir "/workspace" \
  kubricdockerhub/kubruntudev:latest \
  /bin/bash

```
