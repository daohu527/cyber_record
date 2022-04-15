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


class Chunk:
  def __init__(self, proto_chunk_body=None) -> None:
    self._proto_chunk_body = None
    self._index = 0
    self._size = 0

  def swap(self, proto_chunk_body):
    self._index = 0
    self._proto_chunk_body = proto_chunk_body
    self._size = len(proto_chunk_body.messages)

  def next_message(self):
    if self._index >= self._size or self._index < 0:
      return None

    message = self._proto_chunk_body.messages[self._index]
    self._index += 1
    return message

  def end(self):
    return self._index >= self._size

