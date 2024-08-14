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

"""Record chunk struct"""

from cyber_record.cyber.proto import record_pb2


class Chunk:
    """_summary_
    """

    def __init__(self) -> None:
        """_summary_
        """
        self._index = 0
        self._proto_chunk_header = record_pb2.ChunkHeader()
        self._proto_chunk_body = record_pb2.ChunkBody()

    def swap(self, proto_chunk_body):
        """_summary_

        Args:
            proto_chunk_body (_type_): _description_
        """
        self._index = 0
        self._proto_chunk_body = proto_chunk_body
        self._proto_chunk_header.message_number = len(
            proto_chunk_body.messages)

    def clear(self):
        """_summary_
        """
        self._index = 0
        self._proto_chunk_header = record_pb2.ChunkHeader()
        self._proto_chunk_body = record_pb2.ChunkBody()

    def next_message(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        if self._index >= self.num() or self._index < 0:
            return None

        message = self._proto_chunk_body.messages[self._index]
        self._index += 1
        return message

    def end(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self._index >= self.num()

    def add_message(self, topic, msg, t, raw=True):
        """_summary_

        Args:
            topic (_type_): _description_
            msg (_type_): _description_
            t (_type_): _description_
            raw (bool, optional): _description_. Defaults to True.
        """
        if self._proto_chunk_header.begin_time == 0:
            self._proto_chunk_header.begin_time = t
        self._proto_chunk_header.end_time = t

        message = self._proto_chunk_body.messages.add()
        message.channel_name = topic
        message.time = t
        message.content = msg.SerializeToString()

        self._proto_chunk_header.raw_size += len(message.content)
        self._proto_chunk_header.message_number += 1

    def empty(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self.num() == 0

    def interval(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return (self._proto_chunk_header.end_time -
                self._proto_chunk_header.begin_time)

    def size(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self._proto_chunk_header.raw_size

    def num(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return self._proto_chunk_header.message_number
