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


from cyber_record.cyber.proto import record_pb2

from cyber_record.common import CHUNK_RAW_SIZE, CHUNK_INTERVAL


class Chunk:
  def __init__(self) -> None:
    self._index = 0
    self._proto_chunk_header = record_pb2.ChunkHeader()
    self._proto_chunk_body = record_pb2.ChunkBody()

  def swap(self, proto_chunk_body):
    self._index = 0
    self._proto_chunk_header = record_pb2.ChunkHeader()
    self._proto_chunk_body = proto_chunk_body
    self._proto_chunk_header.message_number = len(proto_chunk_body)

  def next_message(self):
    if self._index >= self._num() or self._index < 0:
      return None

    message = self._proto_chunk_body.messages[self._index]
    self._index += 1
    return message

  def end(self):
    return self._index >= self._num()

  def add_message(self, topic, msg, t, raw=True):
    if self._proto_chunk_header.begin_time == 0:
      self._proto_chunk_header.begin_time = t

    self._proto_chunk_header.end_time = t

    message = self._proto_chunk_body.add()
    message.channel_name = topic
    message.time = t
    if raw:
      message.content = msg.SerializeToString()
    else:
      message.content = msg
    self._proto_chunk_header.raw_size += len(message.content)
    self._proto_chunk_header.message_number += 1

  def need_split(self):
    return self._size() >= CHUNK_RAW_SIZE or self._interval() >= CHUNK_INTERVAL

  def _interval(self):
    return self._proto_chunk_header.end_time - \
        self._proto_chunk_header.begin_time

  def _size(self):
    return self._proto_chunk_header.raw_size

  def _num(self):
    self._proto_chunk_header.message_number
