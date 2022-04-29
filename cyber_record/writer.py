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


from google.protobuf import descriptor_pb2

from cyber_record.cyber.proto import record_pb2, proto_desc_pb2
from cyber_record.common import (
  Section,
  HEADER_LENGTH,
  Compression,
)
from cyber_record.file_object.chunk import Chunk


def to_pb_compress(compression):
  if compression == Compression.NONE:
    return record_pb2.COMPRESS_NONE
  elif compression == Compression.BZ2:
    return record_pb2.COMPRESS_BZ2
  elif compression == Compression.LZ4:
    return record_pb2.COMPRESS_LZ4
  else:
    raise Exception()


def get_proto_desc(file_descriptor, proto_desc):
  file_desc_proto = descriptor_pb2.FileDescriptorProto()
  file_descriptor.CopyToProto(file_desc_proto)
  proto_desc.desc = file_desc_proto.SerializeToString()
  # proto_desc.desc = file_descriptor.serialized_pb
  for file_desc in file_descriptor.dependencies:
    depend = proto_desc.dependencies.add()
    get_proto_desc(file_desc, depend)


class Writer():
  def __init__(self, bag) -> None:
    self.bag = bag

    # private
    self._header = record_pb2.Header()
    self._index = record_pb2.Index()
    self._chunk = Chunk()

    self._channel_indexs = {}
    self._chunk_header_indexs = {}
    self._chunk_body_indexs = {}

    self.build_header()

  def build_header(self):
    self._header.major_version = self.bag._major_version
    self._header.minor_version = self.bag._minor_version
    self._header.compress = to_pb_compress(self.bag._compression)
    self._header.chunk_interval = self.bag._chunk_interval
    self._header.segment_interval = self.bag._segment_interval
    self._header.chunk_raw_size = self.bag._chunk_raw_size
    self._header.segment_raw_size = self.bag._segment_raw_size

  def write(self, topic, msg, t, proto_descriptor=None):
    if self._header.begin_time == 0:
      self._header.begin_time = t
    self._header.end_time = t

    self._header.message_number += 1

    if self._need_split_chunk():
      self.flush()
      self._chunk.clear()
      self._header.chunk_number += 1

    if self._new_channel(topic):
      proto_desc = proto_desc_pb2.ProtoDesc()
      get_proto_desc(msg.DESCRIPTOR.file, proto_desc)
      if proto_descriptor is None:
        proto_descriptor = proto_desc

      channel_position = self._cur_position()
      self._add_channel(topic, msg, proto_descriptor)
      self._add_channel_index(channel_position, topic, msg, proto_descriptor)
      self._header.channel_number += 1

    # channel_cache.message_number
    self._channel_indexs[topic].message_number += 1

    self._chunk.add_message(topic, msg, t)

  def write_header(self):
    self.write_proto_record(self._header)

  def write_proto_record(self, proto_record):
    if isinstance(proto_record, record_pb2.Header):
      section_type = record_pb2.SECTION_HEADER
      self._set_position(0)
    elif isinstance(proto_record, record_pb2.Index):
      section_type = record_pb2.SECTION_INDEX
      self._header.index_position = self._cur_position()
    elif isinstance(proto_record, record_pb2.ChunkHeader):
      section_type = record_pb2.SECTION_CHUNK_HEADER
    elif isinstance(proto_record, record_pb2.ChunkBody):
      section_type = record_pb2.SECTION_CHUNK_BODY
    elif isinstance(proto_record, record_pb2.Channel):
      section_type = record_pb2.SECTION_CHANNEL
    else:
      raise Exception()

    record = proto_record.SerializeToString()
    section = Section(section_type, len(record))
    self._write_section(section)
    self._write(record)

    if section_type == record_pb2.SECTION_HEADER:
      if HEADER_LENGTH < len(record):
        raise Exception()
      reserved_bytes = bytes(HEADER_LENGTH - len(record))
      self._write(reserved_bytes)

    # Get the position of the end of the file
    self._header.size = self._cur_position()


  def flush(self):
    if not self._chunk.empty():
      chunk_header_position = self._cur_position()
      self.write_proto_record(self._chunk._proto_chunk_header)
      self._add_chunk_header_index(chunk_header_position,
                                   self._chunk._proto_chunk_header)

      chunk_body_position = self._cur_position()
      self.write_proto_record(self._chunk._proto_chunk_body)
      self._add_chunk_body_index(chunk_body_position, self._chunk.num())

      self._header.chunk_number += 1

  def close(self):
    self.flush()
    self.write_proto_record(self._index)

    self._header.is_complete = True
    self.write_header()

  def _add_channel(self, topic, msg, proto_desc):
    proto_channel = record_pb2.Channel()
    proto_channel.name = topic
    proto_channel.message_type = '{}.{}'.format(msg.DESCRIPTOR.file.package, type(msg).__name__)
    proto_channel.proto_desc = proto_desc.SerializeToString()
    self.write_proto_record(proto_channel)

  def _add_channel_index(self, channel_position, topic, msg, proto_desc):
    channel_index = self._index.indexes.add()
    channel_index.type = record_pb2.SECTION_CHANNEL
    channel_index.position = channel_position
    channel_index.channel_cache.message_number = 0
    channel_index.channel_cache.name = topic
    channel_index.channel_cache.message_type = '{}.{}'.format(msg.DESCRIPTOR.file.package, type(msg).__name__)
    channel_index.channel_cache.proto_desc = proto_desc.SerializeToString()

    # add to dict
    self._channel_indexs[topic] = channel_index.channel_cache

  def _add_chunk_header_index(self, chunk_header_position, proto_chunk_header):
    chunk_header_index = self._index.indexes.add()
    chunk_header_index.type = record_pb2.SECTION_CHUNK_HEADER
    chunk_header_index.position = chunk_header_position

    chunk_header_cache = chunk_header_index.chunk_header_cache
    chunk_header_cache.message_number = proto_chunk_header.message_number
    chunk_header_cache.begin_time = proto_chunk_header.begin_time
    chunk_header_cache.end_time = proto_chunk_header.end_time
    chunk_header_cache.raw_size = proto_chunk_header.raw_size

  def _add_chunk_body_index(self, chunk_body_position, message_number):
    chunk_body_index = self._index.indexes.add()
    chunk_body_index.type = record_pb2.SECTION_CHUNK_BODY
    chunk_body_index.position = chunk_body_position
    chunk_body_index.chunk_body_cache.message_number = message_number

  def _need_split_chunk(self):
    return (self._chunk.size() >= self._header.chunk_raw_size or
            self._chunk.interval() >= self._header.chunk_interval)

  def _need_split_file(self):
    return ((self._header.end_time - self._header.begin_time >=
            self._header.segment_interval) or
            (self._header.size >= self._header.segment_raw_size))

  def _new_channel(self, topic):
    return topic not in self._channel_indexs

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
