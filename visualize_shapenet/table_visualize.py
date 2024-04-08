# Copyright 2024 The Kubric Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import kubric as kb
from kubric.renderer.blender import Blender as KubricRenderer

logging.basicConfig(level="INFO")



# --- populate the scene with objects, lights, cameras

import os
print("loading shapenet")
source_path = os.getenv("SHAPENET_GCP_BUCKET", "gs://kubric-unlisted/assets/ShapeNetCore.v2.json")
shapenet = kb.AssetSource.from_manifest(source_path)
print("Loading table ids")

table_ids = [name for name, spec in shapenet._assets.items()
                if spec["metadata"]["category"] == "table"]

from tqdm import tqdm
for asset_id in tqdm(table_ids[96+13:]):
    try:
        scene = kb.Scene(resolution=(256, 256))
        renderer = KubricRenderer(scene)

        obj = shapenet.create(asset_id=asset_id)
        name = asset_id[9:]

        obj.quaternion = kb.Quaternion(axis=[1, 0, 0], degrees=90)
        obj.position = obj.position - (0, 0, obj.aabbox[0][2]) 
        print(obj.scale) 
        scene.add(obj)

        scene += kb.PerspectiveCamera(name="camera", position=(2, -1, 1),
                                look_at=(0, 0, 0))
        scene += kb.PointLight(name="sun", position=(-1, -0.5, 1),
                                look_at=(0, 0, 0.5), intensity=50)
        scene += kb.PointLight(name="sun2", position=(-2, -1, 0),
                                look_at=(0, 0, 0), intensity=50)
        scene += kb.PointLight(name="sun3", position=(3, -1.5, 0),
                            look_at=(0, 0, 0), intensity=25)

        # renderer.save_state(f"shapenet_tables/model/{name}.blend")
        frame = renderer.render_still()

        # --- save the output as pngs
        kb.write_png(frame["rgba"], f"shapenet_tables/img/{name}.png")
    except:
        print("Can't load table data")
# --- create scene and attach a renderer to it

