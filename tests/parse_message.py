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

from cyber_record.record import Record


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
  else:
    print("{} not parse".format(topic))

f.close()
