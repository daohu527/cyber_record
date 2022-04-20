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
import cv2
import numpy as np
import pypcd

from cyber_record.record import Record

image_num = 0
pcd_num = 0

def parse_pose(pose):
  '''
  save pose to csv file
  '''
  writer.writerow([pose.header.timestamp_sec, pose.pose.position.x, \
      pose.pose.position.y, pose.pose.position.z, pose.pose.orientation.qx, \
      pose.pose.orientation.qy, pose.pose.orientation.qz, \
      pose.pose.orientation.qw, pose.pose.heading])

def parse_chassis(chassis):
  print(chassis)

def parse_prediction(prediction):
  print(prediction)

def parse_routing_response_history(routing_response_history):
  print(routing_response_history)

def parse_planning(planning):
  print(planning)

def parse_camera(image):
  if image.encoding == 'rgb8' or image.encoding == 'bgr8':
    if image.step != image.width * 3:
      print('Image.step %d does not equal to Image.width %d * 3 for color image.'
          % (image.step, image.width))
      return False
  elif image.encoding == 'gray' or image.encoding == 'y':
    if image.step != image.width:
      print('Image.step %d does not equal to Image.width %d or gray image.'
          % (image.step, image.width))
      return False
  else:
    print('Unsupported image encoding type: {}.'.format(image.encoding))
    return False

  channel_num = image.step // image.width
  image_mat = np.fromstring(image.data, dtype=np.uint8).reshape(
      (image.height, image.width, channel_num))

  global image_num
  if image.measurement_time:
    image_file = '{}.jpg'.format(image.measurement_time)
  else:
    image_file = '{}.jpg'.format(image_num)
    image_num += 1

  if image.encoding == 'rgb8':
    cv2.imwrite(image_file, cv2.cvtColor(image_mat, cv2.COLOR_RGB2BGR))
  else:
    cv2.imwrite(image_file, image_mat)

  # cv2.imshow("image", image_mat)
  # cv2.waitKey()


def convert_xyzit_pb_to_array(xyz_i_t, data_type):
  arr = np.zeros(len(xyz_i_t), dtype=data_type)
  for i, point in enumerate(xyz_i_t):
      # change timestamp to timestamp_sec
      arr[i] = (point.x, point.y, point.z,
                point.intensity, point.timestamp/1e9)
  return arr


def make_xyzit_point_cloud(xyz_i_t):
  """
  Make a pointcloud object from PointXYZIT message, as Pointcloud.proto.
  message PointXYZIT {
    optional float x = 1 [default = nan];
    optional float y = 2 [default = nan];
    optional float z = 3 [default = nan];
    optional uint32 intensity = 4 [default = 0];
    optional uint64 timestamp = 5 [default = 0];
  }
  """

  md = {'version': .7,
        'fields': ['x', 'y', 'z', 'intensity', 'timestamp'],
        'count': [1, 1, 1, 1, 1],
        'width': len(xyz_i_t),
        'height': 1,
        'viewpoint': [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
        'points': len(xyz_i_t),
        'type': ['F', 'F', 'F', 'U', 'F'],
        'size': [4, 4, 4, 4, 8],
        'data': 'binary_compressed'}
  typenames = []
  for t, s in zip(md['type'], md['size']):
      np_type = pypcd.pcd_type_to_numpy_type[(t, s)]
      typenames.append(np_type)

  np_dtype = np.dtype(list(zip(md['fields'], typenames)))
  pc_data = convert_xyzit_pb_to_array(xyz_i_t, data_type=np_dtype)
  pc = pypcd.PointCloud(md, pc_data)
  return pc


def parse_point_cloud(pointcloud):
  global pcd_num
  if pointcloud.measurement_time:
    pcd_file = '{}.pcd'.format(pointcloud.measurement_time)
  else:
    pcd_file = '{}.pcd'.format(pcd_num)
    pcd_num += 1

  pc_meta = make_xyzit_point_cloud(pointcloud.point)
  pypcd.save_point_cloud_bin(pc_meta, pcd_file)


if __name__ == "__main__":
  # csv
  f = open("message.csv", 'w')
  writer = csv.writer(f)

  # bag
  file_name = "example.record.00000"
  record = Record(file_name)

  for topic, message, t in record.read_messages():
    if topic == "/apollo/localization/pose":
      parse_pose(message)
    elif topic == "/apollo/canbus/chassis":
      parse_chassis(message)
    elif topic == "/apollo/prediction":
      parse_prediction(message)
    elif topic == "/apollo/routing_response_history":
      parse_routing_response_history(message)
    elif topic == "/apollo/planning":
      parse_planning(message)
    elif topic == "/apollo/sensor/camera/front_6mm/image":
      parse_camera(message)
    elif topic == "/apollo/sensor/lidar32/compensator/PointCloud2":
      parse_point_cloud(message)
    else:
      print("{} not parse".format(topic))

  f.close()
