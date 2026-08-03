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


import csv
import os

from cyber_record.record import Record
from cyber_record.message_tools import to_csv, ImageParser, PointCloudParser


def parse_pose(pose, writer):
    """
    save pose to csv file using provided `writer`.
    """
    line = to_csv([pose.header.timestamp_sec, pose.pose])
    writer.writerow(line)


def parse_chassis(chassis):
    pass


def parse_prediction(prediction):
    pass


def parse_routing_response_history(routing_response_history):
    pass


def parse_planning(planning):
    pass


def parse_image(image):
    image_parser.parse(image)


if __name__ == "__main__":
    base_dir = os.path.dirname(__file__)
    out_path = os.path.join(base_dir, 'message.csv')

    # bag
    assets = os.path.join(base_dir, 'assets')

    candidates = [
        os.path.join(assets, 'example.record.00000'),
        os.path.join(assets, 'example_w.record.00000'),
    ]

    for cand in candidates:
        if os.path.exists(cand):
            file_name = cand
            break
    else:
        raise FileNotFoundError(f"No record found in {assets}")
    print(f"Using record: {file_name}", flush=True)
    record = Record(file_name)

    image_parser = ImageParser("../tests")
    pointcloud_parser = PointCloudParser("../right")

    with open(out_path, 'w', newline='') as f:
        writer = csv.writer(f)

        for topic, message, t in record.read_messages_fallback():
            if topic == "/apollo/localization/pose":
                parse_pose(message, writer)
            elif topic == "/apollo/canbus/chassis":
                parse_chassis(message)
        # elif topic == "/apollo/prediction":
        #     parse_prediction(message)
        # elif topic == "/apollo/routing_response_history":
        #     parse_routing_response_history(message)
        # elif topic == "/apollo/planning":
        #     parse_planning(message)
        # elif topic == "/apollo/sensor/camera/front_6mm/image":
        #     parse_image(message)
        # elif topic == "/apollo/sensor/vanjeelidar/left_front/PointCloud2":
        #     pointcloud_parser.parse(message, t)
        else:
            pass
