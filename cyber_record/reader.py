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


from google.protobuf import message_factory, descriptor_pb2, descriptor_pool


from cyber_record.cyber.proto import record_pb2, proto_desc_pb2
from cyber_record.file_object.chunk import Chunk
from cyber_record.record_exception import RecordException
from cyber_record.common import Section, SECTION_LENGTH, HEADER_LENGTH


class Reader:
  def __init__(self, bag) -> None:
    self.bag = bag
    self.chunk_header_indexs = []
    self.chunk_body_indexs = []
    self.sorted_chunk_indexs = []
    self.channels = {}
    self.desc_pool = descriptor_pool.DescriptorPool()

    self.message_type_pool = {}
    self.chunk = Chunk()
    self.message_index = 0

  def _fill_header(self, header):
    self.bag._version = "{}.{}".format(header.major_version, \
        header.minor_version)
    self.bag._size = header.size
    self.bag._message_number = header.message_number
    self.bag._start_time = header.begin_time
    self.bag._end_time = header.end_time

  def _sort_chunk_indexs(self):
    self.sorted_chunk_indexs = sorted( \
      zip(self.chunk_header_indexs, self.chunk_body_indexs), \
      key=lambda x: x[0].chunk_header_cache.begin_time)

  def start_reading(self):
    header = self.read_header()
    self._fill_header(header)
    print(header)

    index = self.read_index(header)
    for single_index in index.indexes:
      if single_index.type == record_pb2.SECTION_CHUNK_HEADER:
        self.chunk_header_indexs.append(single_index)
      elif single_index.type == record_pb2.SECTION_CHUNK_BODY:
        self.chunk_body_indexs.append(single_index)
      elif single_index.type == record_pb2.SECTION_CHANNEL:
        name = single_index.channel_cache.name
        self.channels[name] = single_index.channel_cache
      else:
        print("Unknown Index type!")

    self._sort_chunk_indexs()
    # print(index)

    self._create_message_type_pool()

    self._set_position(HEADER_LENGTH + SECTION_LENGTH)

  def reindex(self):
    pass

  def get_channel_cache(self, topic_filters):
    filtered_channel_cache = []
    for channel_name in self.channels:
      if topic_filters is None or channel_name not in topic_filters:
        filtered_channel_cache.append(self.channels[channel_name])
    return filtered_channel_cache

  def _is_valid_topic(self, topic, topics):
    if topics is None:
      return True

    return topic in set(topics)

  def _is_valid_time(self, cur_time, start_time, end_time):
    if start_time and cur_time < start_time:
      return False
    if end_time and cur_time > end_time:
      return False
    return True

  def _get_chunk_body_indexs(self, start_time, end_time):
    for chunk_header_index, chunk_body_index in self.sorted_chunk_indexs:
      if start_time and \
          chunk_header_index.chunk_header_cache.end_time < start_time:
        continue

      if end_time and \
          chunk_header_index.chunk_header_cache.begin_time > end_time:
        continue
      # Todo(zero): should be chunk_body_index, there maybe a bug in apollo!!!
      yield chunk_body_index

  def read_messages(self, topics, start_time, end_time):
    for chunk_body_index in self._get_chunk_body_indexs(start_time, end_time):
      # print(chunk_body_index)
      proto_chunk_body = self.read_chunk_body(chunk_body_index.position)
      if proto_chunk_body is None:
        continue
      self.chunk.swap(proto_chunk_body)

      while not self.chunk.end():
        single_message = self.chunk.next_message()
        if self._is_valid_topic(single_message.channel_name, topics) and \
           self._is_valid_time(single_message.time, start_time, end_time):
          proto_message = self._create_message(single_message)
          yield single_message.channel_name, proto_message, single_message.time

  def read_messages_fallback(self, topics, start_time, end_time):
    """
    deprecated
    """
    while self.message_index < self.bag._message_number:
      if self.chunk.end():
        self._read_next_chunk()

      single_message = self.chunk.next_message()
      proto_message = self._create_message(single_message)
      self.message_index += 1
      yield single_message.channel_name, proto_message, single_message.time

  def read_header(self):
    self._set_position(0)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_HEADER:
      return None

    proto_header = record_pb2.Header()
    data = self._read(section.size)

    proto_header.ParseFromString(data)

    self._set_position(HEADER_LENGTH + SECTION_LENGTH)
    return proto_header

  def read_index(self, header):
    self._set_position(header.index_position)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_INDEX:
      return None

    proto_index = record_pb2.Index()
    data = self._read(section.size)

    proto_index.ParseFromString(data)
    return proto_index

  def read_chunk_header(self, position):
    self._set_position(position)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_CHUNK_HEADER:
      return None

    chunk_header = record_pb2.ChunkHeader()
    data = self._read(section.size)

    chunk_header.ParseFromString(data)
    return chunk_header

  def read_chunk_body(self, position):
    self._set_position(position)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_CHUNK_BODY:
      return None

    chunk_body = record_pb2.ChunkBody()
    data = self._read(section.size)

    chunk_body.ParseFromString(data)
    return chunk_body

  def _read_section(self, section):
    section.type = int.from_bytes(self._read(4), byteorder='little')
    self._skip_size(4)
    section.size = int.from_bytes(self._read(8), byteorder='little')
    # print(section)

  def _read_next_chunk(self):
    while self.bag._file.tell() != self.bag._size:
      section = Section()
      self._read_section(section)

      if section.type == record_pb2.SECTION_CHUNK_BODY:
        data = self._read(section.size)
        proto_chunk_body = record_pb2.ChunkBody()
        proto_chunk_body.ParseFromString(data)
        self.chunk.swap(proto_chunk_body)
        return True
      else:
        self._skip_size(section.size)
    else:
      return False

  def _add_dependency(self, proto_desc):
    if proto_desc is None:
      return

    file_desc_proto = descriptor_pb2.FileDescriptorProto()
    file_desc_proto.ParseFromString(proto_desc.desc)
    for dependency in proto_desc.dependencies:
      self._add_dependency(dependency)
    self.desc_pool.Add(file_desc_proto)
    # print(file_desc_proto)

  def _create_message_type_pool(self):
    for channel_name, channel_cache in self.channels.items():
      proto_desc = proto_desc_pb2.ProtoDesc()
      proto_desc.ParseFromString(channel_cache.proto_desc)
      self._add_dependency(proto_desc)

      # print(channel_cache.message_type)
      descriptor = self.desc_pool.FindMessageTypeByName(channel_cache.message_type)
      message_type = message_factory.MessageFactory().GetPrototype(descriptor)
      self.message_type_pool.update({channel_name: message_type})

  def _create_message(self, single_message):
    message_type = self.message_type_pool.get(single_message.channel_name, None)

    if message_type is None:
      return None
    proto_message = message_type()
    proto_message.ParseFromString(single_message.content)

    return proto_message

  def _read(self, size):
    data = self.bag._file.read(size)
    if len(data) != size:
      raise RecordException('expecting {} bytes, read {}'.format(size, len(data)))
    return data

  def _set_position(self, position):
    self.bag._file.seek(position)

  def _cur_position(self):
    return self.bag._file.tell()

  def _skip_size(self, data_size):
    self.bag._file.seek(data_size, 1)

  def _skip_record(self):
    section = Section()
    self._read_section(section)
    self._skip_size(section.size)
