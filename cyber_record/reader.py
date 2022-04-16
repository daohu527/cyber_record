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


SECTION_LENGTH = 16
HEADER_LENGTH = 2048


class Section:
  def __init__(self, section_type=None, data_size=0) -> None:
    self.type = section_type
    self.size = data_size

  def __str__(self):
    return "Section type: {}, size: {}".format(self.type, self.size)


class Reader:
  def __init__(self, bag) -> None:
    self.bag = bag
    self.chunk_header_indexs = []
    self.chunk_body_indexs = []
    self.channels = {}
    self.desc_pool = descriptor_pool.DescriptorPool()

    self.message_type_pool = {}
    self.chunk = Chunk()
    self.message_index = 0


  def start_reading(self):
    header = self.read_header()
    self.bag._size = header.size
    self.bag._message_number = header.message_number
    # print(header)

    indexs = self.read_indexs(header)
    for single_index in indexs.indexes:
      if single_index.type == record_pb2.SECTION_CHUNK_HEADER:
        self.chunk_header_indexs.append(single_index)
      elif single_index.type == record_pb2.SECTION_CHUNK_BODY:
        self.chunk_body_indexs.append(single_index)
      elif single_index.type == record_pb2.SECTION_CHANNEL:
        name = single_index.channel_cache.name
        self.channels[name] = single_index.channel_cache
      else:
        print("Unknown Index type!")

    # print(indexs)

    self._create_message_type_pool()

    self.bag._file.seek(HEADER_LENGTH + SECTION_LENGTH, 0)


  def reindex(self):
    pass

  def read_messages(self, topics, start_time, end_time):
    while self.message_index < self.bag._message_number:
      if self.chunk.end():
        self.read_next_chunk()

      single_message = self.chunk.next_message()
      proto_message = self.create_message(single_message)
      self.message_index += 1
      yield single_message.channel_name, proto_message, single_message.time

  def _read_section(self, section):
    section.type = int.from_bytes(self.bag._file.read(4), byteorder='little')
    self.bag._file.seek(4, 1)
    section.size = int.from_bytes(self.bag._file.read(8), byteorder='little')
    # print(section)

  def read_header(self):
    self.bag._file_header_pos = self.bag._file.seek(0, 0)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_HEADER:
      return None

    proto_header = record_pb2.Header()
    data = self.bag._file.read(section.size)
    if len(data) != section.size:
      print("Header is incomplete, \
          actual size: {}, required size: {}".format(len(data), section.size))
      return None

    proto_header.ParseFromString(data)
    self.bag._file.seek(HEADER_LENGTH + SECTION_LENGTH, 0)
    return proto_header


  def read_indexs(self, header):
    self.bag._file.seek(header.index_position, 0)

    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_INDEX:
      return None

    proto_indexs = record_pb2.Index()
    data = self.bag._file.read(section.size)
    if len(data) != section.size:
      print("Index is incomplete, \
          actual size: {}, required size: {}".format(len(data), section.size))
      return None

    proto_indexs.ParseFromString(data)
    return proto_indexs

  def read_chunk_body(self, chunk_body_index):
    self.bag._file.seek(chunk_body_index.position, 0)
    section = Section()
    self._read_section(section)

    if section.type != record_pb2.SECTION_CHUNK_BODY:
      return None

    chunk_body = record_pb2.ChunkBody()
    data = self.bag._file.read(section.size)
    if len(data) != section.size:
      print("ChunkBody is incomplete, \
          actual size: {}, required size: {}".format(len(data), section.size))
      return None

    chunk_body.ParseFromString(data)
    return chunk_body


  def read_chunk_header(self):
    pass

  def read_next_chunk(self):
    while self.bag._file.tell() != self.bag._size:
      section = Section()
      self._read_section(section)

      if section.type == record_pb2.SECTION_CHUNK_BODY:
        data = self.bag._file.read(section.size)
        proto_chunk_body = record_pb2.ChunkBody()
        proto_chunk_body.ParseFromString(data)
        self.chunk.swap(proto_chunk_body)
        return True
      else:
        self.bag._file.seek(section.size, 1)
    else:
      return False


  def read_records(self):
    self.bag._file.seek(HEADER_LENGTH + SECTION_LENGTH, 0)

    while self.bag._file.tell() != self.bag._size:
      section = Section()
      self._read_section(section)
      data = self.bag._file.read(section.size)

      if section.type == record_pb2.SECTION_CHUNK_HEADER:
        proto_chunk_header = record_pb2.ChunkHeader()
        proto_chunk_header.ParseFromString(data)
      elif section.type == record_pb2.SECTION_INDEX:
        proto_indexs = record_pb2.Index()
        proto_indexs.ParseFromString(data)
      elif section.type == record_pb2.SECTION_CHUNK_BODY:
        proto_chunk_body = record_pb2.ChunkBody()
        proto_chunk_body.ParseFromString(data)
        for message in proto_chunk_body.messages:
          self.create_message(message)
      else:
        pass

  def add_dependency(self, proto_desc):
    if proto_desc is None:
      return

    file_desc_proto = descriptor_pb2.FileDescriptorProto()
    file_desc_proto.ParseFromString(proto_desc.desc)
    for dependency in proto_desc.dependencies:
      self.add_dependency(dependency)
    self.desc_pool.Add(file_desc_proto)


  def _create_message_type_pool(self):
    for channel_name, channel_cache in self.channels.items():
      proto_desc = proto_desc_pb2.ProtoDesc()
      proto_desc.ParseFromString(channel_cache.proto_desc)
      self.add_dependency(proto_desc)

      descriptor = self.desc_pool.FindMessageTypeByName(channel_cache.message_type)
      message_type = message_factory.MessageFactory().GetPrototype(descriptor)
      self.message_type_pool.update({channel_name: message_type})


  def create_message(self, single_message):
    message_type = self.message_type_pool.get(single_message.channel_name, None)

    if message_type is None:
      return None
    proto_message = message_type()
    proto_message.ParseFromString(single_message.content)

    return proto_message
