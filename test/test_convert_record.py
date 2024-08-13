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


def convert_record():
    read_file_name = "test.record"
    write_file_name = "out.record"

    r_record = Record(read_file_name)
    with Record(write_file_name, mode='w') as w_record:
        for topic, message, t in r_record.read_messages_fallback():
            # print("{}, {}, {}".format(topic, type(message), t))
            if topic == '/apollo/sensor/camera/traffic/image_long':
                message.header.frame_id = "camera_front_12mm"
                message.frame_id = "camera_front_12mm"
                w_record.write(
                    '/apollo/sensor/camera/front_12mm/image', message, t)
            elif topic == '/apollo/sensor/camera/front_6mm/image':
                message.header.frame_id = "camera_front_6mm"
                message.frame_id = "camera_front_6mm"
                w_record.write(topic, message, t)
            else:
                w_record.write(topic, message, t)


if __name__ == "__main__":
    convert_record()
