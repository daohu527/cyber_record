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


from cyber_record.cyber.proto import record_pb2, proto_desc_pb2
from cyber_record.common import Section, HEADER_LENGTH
from cyber_record.file_object.chunk import Chunk


class Writer():
  def __init__(self, bag) -> None:
    self.bag = bag

    # private
    self._header = record_pb2.Header()
    self._chunk = Chunk()

  def write(self, topic, msg, t, raw=True, proto_descriptor=None):
    if self._chunk.need_split():
      self.write_chunk_header(self._chunk._proto_chunk_header)
      self.write_chunk_body(self._chunk._proto_chunk_body)
      self._chunk.swap(record_pb2.ChunkBody())
    self._chunk.add_message(topic, msg, t, raw=True)

  def write_header(self):
    self._set_position(0)

    header = self._header.SerializeToString()
    section = Section(record_pb2.SECTION_HEADER, len(header))
    self._write_section(section)

    reserved_bytes = bytes(HEADER_LENGTH - len(header))
    self._write(header + reserved_bytes)

  def write_index(self, proto_index):
    index = proto_index.SerializeToString()
    section = Section(record_pb2.SECTION_INDEX, len(index))
    self._write_section(section)
    self._write(index)

  def write_chunk_header(self, proto_chunk_header):
    chunk_header = proto_chunk_header.SerializeToString()
    section = Section(record_pb2.SECTION_CHUNK_HEADER, len(chunk_header))
    self._write_section(section)
    self._write(chunk_header)

  def write_chunk_body(self, proto_chunk_body):
    chunk_body = proto_chunk_body.SerializeToString()
    section = Section(record_pb2.SECTION_CHUNK_BODY, len(chunk_body))
    self._write_section(section)
    self._write(chunk_body)

  def flush(self):
    # todo(zero)
    if self._chunk._size() != 0:
      self.write_chunk_header(self._chunk._proto_chunk_header)
      self.write_chunk_body(self._chunk._proto_chunk_body)
    self.write_index()

  def _write_section(self, section):
    section_type = (section.type).to_bytes(8, byteorder='little')
    section_size = (section.size).to_bytes(8, byteorder='little')
    self._write(section_type + section_size)

  def _write(self, data):
    self.bag._file.write(data)

  def _set_position(self, position):
    self.bag._file.seek(position)

  def _cur_position(self):
    return self.bag._file.tell()

  def _skip_size(self, data_size):
    self.bag._file.seek(data_size, 1)
