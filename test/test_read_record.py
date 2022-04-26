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


from cyber_record.record import Record


file_name = "example.record.00000"

def read_all():
  record = Record(file_name)
  for topic, message, t in record.read_messages_fallback():
    print("{}, {}, {}".format(topic, type(message), t))


def read_filter_by_topic():
  record = Record(file_name)
  for topic, message, t in record.read_messages('/apollo/sensor/rs32/Scan'):
    print("{}, {}, {}".format(topic, type(message), t))


def read_filter_by_time():
  record = Record(file_name)
  for topic, message, t in record.read_messages(start_time=1627031535164278940,\
      end_time=1627031535215164773):
    print("{}, {}, {}".format(topic, type(message), t))


def read_filter_by_both():
  record = Record(file_name)
  for topic, message, t in record.read_messages('/apollo/canbus/chassis', \
      start_time=1627031535164278940, end_time=1627031535215164773):
    print("{}, {}, {}".format(topic, type(message), t))


if __name__ == "__main__":
  read_all()
  read_filter_by_topic()
  read_filter_by_time()
  read_filter_by_both()
