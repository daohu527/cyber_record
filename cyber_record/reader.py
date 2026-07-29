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

"""Record reader class"""

import logging

from google.protobuf import message_factory, descriptor_pb2, descriptor_pool

from cyber_record.common import Section, SECTION_LENGTH, HEADER_LENGTH
from cyber_record.cyber.proto import record_pb2, proto_desc_pb2
from cyber_record.file_object.chunk import Chunk
from cyber_record.record_exception import RecordException


class Reader:
    """_summary_
    """

    def __init__(self, bag) -> None:
        """_summary_

        Args:
            bag (_type_): _description_
        """
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
        """_summary_

        Args:
            header (_type_): _description_
        """
        self.bag._version = f"{header.major_version}.{header.minor_version}"
        self.bag._size = header.size
        self.bag._message_number = header.message_number
        self.bag._start_time = header.begin_time
        self.bag._end_time = header.end_time

    def _sort_chunk_indexs(self):
        """_summary_
        """
        self.sorted_chunk_indexs = sorted(
            zip(self.chunk_header_indexs, self.chunk_body_indexs),
            key=lambda x: x[0].chunk_header_cache.begin_time)

    def start_reading(self, allow_unindexed=False):
        """_summary_
        """
        header = self.read_header()
        self._fill_header(header)
        logging.debug(header)

        try:
            index = self.read_index(header)
            if index is None:
                raise RecordException("index section is invalid")
            for single_index in index.indexes:
                if single_index.type == record_pb2.SECTION_CHUNK_HEADER:
                    self.chunk_header_indexs.append(single_index)
                elif single_index.type == record_pb2.SECTION_CHUNK_BODY:
                    self.chunk_body_indexs.append(single_index)
                elif single_index.type == record_pb2.SECTION_CHANNEL:
                    name = single_index.channel_cache.name
                    self.channels[name] = single_index.channel_cache
                else:
                    logging.warning("Unknown Index type!")
            self._sort_chunk_indexs()
            logging.debug(index)
        except Exception as err:
            if not allow_unindexed:
                raise
            logging.warning("Read index failed, fallback to section scan: %s", err)
            self.chunk_header_indexs = []
            self.chunk_body_indexs = []
            self.sorted_chunk_indexs = []
            self.channels = {}
            self._load_channels_from_sections()

        self._create_message_type_pool()

        self._set_position(HEADER_LENGTH + SECTION_LENGTH)

    def _load_channels_from_sections(self):
        """Load channel cache by scanning SECTION_CHANNEL blocks."""
        self._set_position(HEADER_LENGTH + SECTION_LENGTH)
        while self._cur_position() < self.bag._size:
            section = Section()
            try:
                self._read_section(section)
            except RecordException:
                break

            if section.type == record_pb2.SECTION_CHANNEL:
                try:
                    data = self._read(section.size)
                except RecordException:
                    break
                channel = record_pb2.Channel()
                channel.ParseFromString(data)
                channel_cache = record_pb2.ChannelCache()
                channel_cache.name = channel.name
                channel_cache.message_type = channel.message_type
                channel_cache.proto_desc = channel.proto_desc
                self.channels[channel.name] = channel_cache
            elif section.type in (
                record_pb2.SECTION_CHUNK_HEADER,
                record_pb2.SECTION_CHUNK_BODY,
                record_pb2.SECTION_INDEX,
            ):
                self._skip_size(section.size)
                if section.type == record_pb2.SECTION_CHUNK_BODY:
                    break
            else:
                self._skip_size(section.size)

    def reindex(self):
        """_summary_
        """

    def get_channel_cache(self, topic_filters):
        """_summary_

        Args:
            topic_filters (_type_): _description_

        Returns:
            _type_: _description_
        """
        filtered_channel_cache = []
        for channel_name, channel_cache in self.channels.items():
            if topic_filters is None or channel_name not in topic_filters:
                filtered_channel_cache.append(channel_cache)
        return filtered_channel_cache

    def _is_valid_topic(self, topic, topics):
        """_summary_

        Args:
            topic (_type_): _description_
            topics (_type_): _description_

        Returns:
            _type_: _description_
        """
        if topics is None:
            return True

        return topic in topics

    def _is_valid_time(self, cur_time, start_time, end_time):
        """_summary_

        Args:
            cur_time (_type_): _description_
            start_time (_type_): _description_
            end_time (_type_): _description_

        Returns:
            _type_: _description_
        """
        if start_time and cur_time < start_time:
            return False
        if end_time and cur_time > end_time:
            return False
        return True

    def _normalize_topics(self, topics):
        """Convert topic filters to a hash set once for faster lookup."""
        if topics is None:
            return None
        return set(topics)

    def _get_chunk_body_indexs(self, start_time, end_time):
        """_summary_

        Args:
            start_time (_type_): _description_
            end_time (_type_): _description_

        Yields:
            _type_: _description_
        """
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
        """_summary_

        Args:
            topics (_type_): _description_
            start_time (_type_): _description_
            end_time (_type_): _description_

        Yields:
            _type_: _description_
        """
        topics = self._normalize_topics(topics)
        is_valid_topic = self._is_valid_topic
        is_valid_time = self._is_valid_time
        create_message = self._create_message

        for chunk_body_index in self._get_chunk_body_indexs(start_time, end_time):
            logging.debug(chunk_body_index)
            proto_chunk_body = self.read_chunk_body(chunk_body_index.position)
            if proto_chunk_body is None:
                continue
            self.chunk.swap(proto_chunk_body)

            while not self.chunk.end():
                single_message = self.chunk.next_message()
                if is_valid_topic(single_message.channel_name, topics) and \
                   is_valid_time(single_message.time, start_time, end_time):
                    proto_message = create_message(single_message)
                    yield single_message.channel_name, proto_message, single_message.time

    def read_messages_fallback(self, topics, start_time, end_time):
        """
        deprecated: use read_messages_section_scan
        """
        return self.read_messages_section_scan(topics, start_time, end_time)

    def read_messages_section_scan(self, topics, start_time, end_time):
        """
        Sequentially scan all sections and parse SECTION_CHUNK_BODY in-place.
        Unlike read_messages, this does not rely on index chunk positions.
        """
        topics = self._normalize_topics(topics)
        is_valid_topic = self._is_valid_topic
        is_valid_time = self._is_valid_time
        create_message = self._create_message

        start_pos = HEADER_LENGTH + SECTION_LENGTH
        self._set_position(start_pos)
        self.chunk.clear()

        cur = self._cur_position()
        self.bag._file.seek(0, 2)
        file_size = self.bag._file.tell()
        self._set_position(cur)

        skip_next_chunk_body = False

        while self._cur_position() < file_size:
            section = Section()
            try:
                self._read_section(section)
            except RecordException:
                break

            if self._cur_position() + section.size > file_size:
                break

            if section.type == record_pb2.SECTION_CHUNK_HEADER:
                try:
                    data = self._read(section.size)
                except RecordException:
                    break
                chunk_header = record_pb2.ChunkHeader()
                chunk_header.ParseFromString(data)
                if start_time and chunk_header.end_time < start_time:
                    skip_next_chunk_body = True
                elif end_time and chunk_header.begin_time > end_time:
                    skip_next_chunk_body = True
                else:
                    skip_next_chunk_body = False
            elif section.type == record_pb2.SECTION_CHUNK_BODY:
                if skip_next_chunk_body:
                    self._skip_size(section.size)
                    skip_next_chunk_body = False
                    continue

                try:
                    data = self._read(section.size)
                except RecordException:
                    break

                proto_chunk_body = record_pb2.ChunkBody()
                proto_chunk_body.ParseFromString(data)
                self.chunk.swap(proto_chunk_body)
                while not self.chunk.end():
                    single_message = self.chunk.next_message()
                    if single_message is None:
                        break
                    if is_valid_topic(single_message.channel_name, topics) and \
                       is_valid_time(single_message.time, start_time, end_time):
                        proto_message = create_message(single_message)
                        yield single_message.channel_name, proto_message, single_message.time
            else:
                self._skip_size(section.size)

    def read_header(self):
        """_summary_

        Returns:
            _type_: _description_
        """
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
        """_summary_

        Args:
            header (_type_): _description_

        Returns:
            _type_: _description_
        """
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
        """_summary_

        Args:
            position (_type_): _description_

        Returns:
            _type_: _description_
        """
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
        """_summary_

        Args:
            position (_type_): _description_

        Returns:
            _type_: _description_
        """
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
        """_summary_

        Args:
            section (_type_): _description_
        """
        section.type = int.from_bytes(self._read(4), byteorder='little')
        self._skip_size(4)
        section.size = int.from_bytes(self._read(8), byteorder='little')
        logging.debug(section)

    def _read_next_chunk(self):
        """_summary_

        Returns:
            _type_: _description_
        """
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
        """_summary_

        Args:
            proto_desc (_type_): _description_
        """
        if proto_desc is None or not proto_desc.desc:
            return

        file_desc_proto = descriptor_pb2.FileDescriptorProto()
        file_desc_proto.ParseFromString(proto_desc.desc)
        for dependency in proto_desc.dependencies:
            self._add_dependency(dependency)

        try:
            self.desc_pool.FindFileByName(file_desc_proto.name)
        except KeyError:
            self.desc_pool.Add(file_desc_proto)

        logging.debug(file_desc_proto)

    def _create_message_type_pool(self):
        """_summary_
        """
        for channel_name, channel_cache in self.channels.items():
            proto_desc = proto_desc_pb2.ProtoDesc()
            proto_desc.ParseFromString(channel_cache.proto_desc)
            if channel_cache.proto_desc:
                self._add_dependency(proto_desc)

                logging.debug(channel_cache.message_type)
                descriptor = self.desc_pool.FindMessageTypeByName(
                    channel_cache.message_type)
                message_type = message_factory.MessageFactory().GetPrototype(descriptor)
                self.message_type_pool.update({channel_name: message_type})
            else:
                logging.warning(f"{channel_name} has no proto desc!")

    def _create_message(self, single_message):
        """_summary_

        Args:
            single_message (_type_): _description_

        Returns:
            _type_: _description_
        """
        message_type = self.message_type_pool.get(
            single_message.channel_name, None)

        if message_type is None:
            return None
        proto_message = message_type()
        proto_message.ParseFromString(single_message.content)

        return proto_message

    def _read(self, size):
        """_summary_

        Args:
            size (_type_): _description_

        Raises:
            RecordException: _description_

        Returns:
            _type_: _description_
        """
        data = self.bag._file.read(size)
        if len(data) != size:
            raise RecordException(
                f'expecting {size} bytes, read {len(data)}')
        return data

    def _set_position(self, position):
        """_summary_

        Args:
            position (_type_): _description_
        """
        self.bag._file.seek(position)

    def _cur_position(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self.bag._file.tell()

    def _skip_size(self, data_size):
        """_summary_

        Args:
            data_size (_type_): _description_
        """
        self.bag._file.seek(data_size, 1)

    def _skip_record(self):
        """_summary_
        """
        section = Section()
        self._read_section(section)
        self._skip_size(section.size)
