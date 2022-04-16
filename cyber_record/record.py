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


from enum import Enum
import struct
import io
import os.path


from cyber_record.reader import Reader


DEFAULT_CHUNK_SIZE = 200 * 1024 * 1024
MIN_CHUNK_SIZE = 512

class Compression(Enum):
  NONE = 'none'
  BZ2  = 'bz2'
  LZ4 = 'lz4'


class Record(object):
  '''
  The record file
  '''
  def __init__(self, f, mode='r', compression=Compression.NONE, \
      chunk_threshold=DEFAULT_CHUNK_SIZE, allow_unindexed=False, \
      options=None):
    # options
    if options is not None:
      if not isinstance(options, dict):
        raise ValueError('options must be of type dict')
      if 'compression' in options:
        compression = options['compression']
      if 'chunk_threshold' in options:
        chunk_threshold = options['chunk_threshold']

    self._file = None
    self._filename = None
    self._version = None
    self._size = 0
    self._message_number = 0

    self._compression = compression

    assert chunk_threshold >= MIN_CHUNK_SIZE, \
        "chunk_threshold should large than {}".format(MIN_CHUNK_SIZE)
    self._chunk_threshold = chunk_threshold

    self._reader = None

    self._open(f, mode, allow_unindexed)


  def __iter__(self):
    return self.read_messages()

  def __enter__(self):
    pass

  def __exit__(self):
    pass

  @property
  def options(self):
    pass

  @property
  def filename(self):
    pass

  @property
  def version(self):
    pass

  @property
  def mode(self):
    pass

  @property
  def size(self):
    pass

  def _get_chunk_threshold(self):
    pass

  def _set_chunk_threshold(self, chunk_threshold):
    pass

  def read_messages(self, topics=None, start_time=None, end_time=None):
    if topics and isinstance(topics, str):
      topics = [topics]

    return self._reader.read_messages(topics, start_time, end_time)

  def flush(self):
    pass

  def write(self, topic, msg, t=None, raw=False, proto_descriptor=None):
    pass

  def reindex(self):
    pass

  def close(self):
    pass

  def get_message_count(self, topic_filters=None):
    pass

  def __str__(self):
    pass


  # internal interface
  def _read_message(self, position, raw=False, return_proto_descriptor=False):
    pass

  def _get_descriptors(self, topics=None, descriptor_filter=None):
    pass

  def _get_entries(self, descriptors=None, start_time=None, end_time=None):
    pass

  def _get_entry(self, t, descriptors=None):
    pass

  def _clear_index(self):
    pass

  def _open(self, f, mode, allow_unindexed):
    assert f is not None, "filename (or stream) is invalid"

    self._mode = mode

    try:
      if mode == 'r': self._open_read(f)
      elif mode == 'w': self._open_write(f)
      elif mode == 'a': self._open_append(f)
      else:
        raise ValueError('mode {} is invalid'.format(mode))
    except struct.error:
      raise Exception()

  def _is_file(self, f):
    return isinstance(f, io.IOBase)

  def _open_read(self, f):
    if self._is_file(f):
      self._file = f
      self._filename = None
    else:
      self._file = open(f, 'rb')
      self._filename = f

    try:
      self._create_reader()
      self._reader.start_reading()
    except:
      self._close_file()
      raise

  def _open_write(self, f):
    if self._is_file(f):
      self._file = f
      self._filename = None
    else:
      self._file = open(f, 'w+b')
      self._filename = f

    try:
      self._create_reader()
      self._start_writing()
    except:
      self._close_file()
      raise

  def _open_append(self, f):
    if self._is_file(f):
      self._file = f
      self._filename = None
    else:
      self._filename = f
      # if file exists
      if os.path.isfile(f):
        self._file = open(f, 'r+b')
      else:
        self._file = open(f, 'w+b')

    try:
      self._start_appending()
    except:
      self._close_file()
      raise

  def _close_file(self):
    self._file.close()
    self._file = None

  def _create_reader(self):
    self._reader = Reader(self)

  def _start_writing(self):
    self._write_file_header_record(0, 0, 0)

  def _start_appending(self):
    pass

  def _stop_writing(self):
    pass

  def _start_writing_chunk(self):
    pass

  def _get_chunk_offset(self):
    pass

  def _stop_writing_chunk(self):
    pass

  def _set_compression_mode(self, compression):
    pass

  def _write_file_header_record(self):
    pass

  def _write_connection_record(self):
    pass

  def _write_message_data_record(self):
    pass

  def _write_chunk_header(self):
    pass

  def _write_connection_index_record(self):
    pass

  def _write_chunk_info_record(self):
    pass
