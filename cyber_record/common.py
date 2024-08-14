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

"""Common functions"""

from enum import Enum

SECTION_LENGTH = 16
HEADER_LENGTH = 2048
CHUNK_INTERVAL = 20 * 1000 * 1000 * 1000    # 20s
SEGMENT_INTERVAL = 60 * 1000 * 1000 * 1000  # 60s
CHUNK_RAW_SIZE = 200 * 1024 * 1024     # 200MB
SEGMENT_RAW_SIZE = 2048 * 1024 * 1024  # 2GB

MIN_CHUNK_SIZE = 512

RECORD_MAJOR_VERSION = 1
RECORD_MINOR_VERSION = 0


class Compression(Enum):
    """_summary_

    Args:
        Enum (_type_): _description_
    """
    NONE = 'none'
    BZ2 = 'bz2'
    LZ4 = 'lz4'


class Section:
    """_summary_
    """

    def __init__(self, section_type=None, data_size=0) -> None:
        """_summary_

        Args:
            section_type (_type_, optional): _description_. Defaults to None.
            data_size (int, optional): _description_. Defaults to 0.
        """
        self.type = section_type
        self.size = data_size

    def __str__(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        return f"Section type: {self.type}, size: {self.size}"
