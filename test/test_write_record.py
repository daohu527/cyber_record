#!/usr/bin/env python

# Copyright 2022 daohu527 <daohu527@gmail.com>
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


import time
import os

from PIL import Image

from modules.common_msgs.map_msgs import map_pb2
from cyber_record.record import Record
from record_msg.builder import ImageBuilder, PointCloudBuilder


BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.join(BASE_DIR, 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)


def write_message():
    pb_map = map_pb2.Map()
    pb_map.header.version = 'hello'.encode()

    write_file_name = os.path.join(ASSETS_DIR, "example_w.record.00000")
    with Record(write_file_name, mode='w') as record:
        record.write('/apollo/map', pb_map, int(time.time() * 1e9))


def read_write_message():
    read_path = "example.record.00000"
    # prefer assets location if moved
    if not os.path.exists(read_path):
        read_path = os.path.join(ASSETS_DIR, 'example.record.00000')

    write_path = os.path.join(ASSETS_DIR, "example_w.record.00001")

    if not os.path.exists(read_path):
        print(f"Error: {read_path} not found.")
        return

    with Record(read_path) as r_record, Record(write_path, mode="w") as w_record:
        for topic, message, t in r_record.read_messages_fallback():
            print(f"Topic: {topic}, Type: {type(message)}, Time: {t}")
            w_record.write(topic, message, t)


def write_image():
    img_path = os.path.join(ASSETS_DIR, "test.jpg")
    if not os.path.exists(img_path):
        return

    image_builder = ImageBuilder()
    out_path = os.path.join(ASSETS_DIR, "example_w.record.00002")
    with Record(out_path, mode="w") as record:
        pb_image = image_builder.build(img_path, frame_id="camera", encoding="rgb8")
        record.write("/apollo/sensor/camera/front_6mm/image", pb_image)


def write_point_cloud():
    point_cloud_builder = PointCloudBuilder()
    write_file_name = os.path.join(ASSETS_DIR, "example_w.record.00003")
    with Record(write_file_name, mode='w') as record:
        pcd_path = os.path.join(ASSETS_DIR, 'test.pcd')
        pb_point_cloud = point_cloud_builder.build(pcd_path, 'velodyne')
        record.write('/apollo/sensor/lidar32/compensator/PointCloud2',
                     pb_point_cloud,
                     int(time.time() * 1e9))


if __name__ == "__main__":
    write_message()
    read_write_message()
    write_image()
    write_point_cloud()
