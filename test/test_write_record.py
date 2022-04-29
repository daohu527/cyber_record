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

from cyber_record.record import Record
from modules.map.proto import map_pb2

read_file_name = "example.record.00000"
write_file_name = "example_w.record.00000"


def write_message():
  pb_map = map_pb2.Map()
  pb_map.header.version = 'hello'.encode()
  with Record(write_file_name, mode='w') as record:
    record.write('/apollo/map', pb_map, int(time.time() * 1e9))


def read_write_message():
  r_record = Record(read_file_name)
  with Record(write_file_name, mode='w') as w_record:
    for topic, message, t in r_record.read_messages_fallback():
      print("{}, {}, {}".format(topic, type(message), t))
      w_record.write(topic, message, t)


if __name__ == "__main__":
  # write_message()
  read_write_message()
