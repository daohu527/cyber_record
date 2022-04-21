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
import time


from cyber_record.reader import Reader


DEFAULT_CHUNK_SIZE = 200 * 1024 * 1024
MIN_CHUNK_SIZE = 512

class Compression(Enum):
  NONE = 'none'
  BZ2  = 'bz2'
  LZ4 = 'lz4'


class Record(object):
  """
  Serialize messages to and from a single file on disk using record format.
  """
  def __init__(self, f, mode='r', compression=Compression.NONE, \
      chunk_threshold=DEFAULT_CHUNK_SIZE, allow_unindexed=False, \
      options=None):
    """
    Open a bag file.  The mode can be 'r', 'w', or 'a' for reading (default),
    writing or appending.  The file will be created if it doesn't exist
    when opened for writing or appending; it will be truncated when opened
    for writing.  Simultaneous reading and writing is allowed when in writing
    or appending mode.

    Args:
        f (_type_): _description_
        mode (str, optional): _description_. Defaults to 'r'.
        compression (_type_, optional): _description_. Defaults to Compression.NONE.
        allow_unindexed (bool, optional): _description_. Defaults to False.

    Raises:
        ValueError: _description_
    """
    # options
    if options is not None:
      if not isinstance(options, dict):
        raise ValueError('options must be of type dict')
      if 'compression' in options:
        compression = options['compression']
      if 'chunk_threshold' in options:
        chunk_threshold = options['chunk_threshold']

    self._file     = None
    self._filename = None
    self._version  = None

    self._size           = 0
    self._message_number = 0

    self._start_time = 0
    self._end_time   = 0

    allowed_compressions = set(item for item in Compression)
    if compression not in allowed_compressions:
      raise ValueError('compression must be one of: {}'.format(allowed_compressions))
    self._compression = compression

    assert chunk_threshold >= MIN_CHUNK_SIZE, \
        "chunk_threshold should large than {}".format(MIN_CHUNK_SIZE)
    self._chunk_threshold = chunk_threshold

    self._reader = None
    self._encryptor = None

    self._open(f, mode, allow_unindexed)


  def __iter__(self):
    return self.read_messages()

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.close()

  @property
  def options(self):
    return {'compression' : self._compression, \
            'chunk_threshold' : self._chunk_threshold}

  @property
  def filename(self):
    return self._filename

  @property
  def version(self):
    return self._version

  @property
  def mode(self):
    return self._mode

  @property
  def size(self):
    return self._size

  def _get_compression(self):
    return self._compression

  def _set_compression(self, compression):
    allowed_compressions = set(item.value for item in Compression)
    if compression not in allowed_compressions:
      raise ValueError('compression must be one of: {}'.format(allowed_compressions))

    self._compression = compression

  compression = property(_get_compression, _set_compression)


  def _get_chunk_threshold(self):
    return self._chunk_threshold

  def _set_chunk_threshold(self, chunk_threshold):
    assert chunk_threshold >= MIN_CHUNK_SIZE, \
        "chunk_threshold should large than {}".format(MIN_CHUNK_SIZE)
    self._chunk_threshold = chunk_threshold

  chunk_threshold = property(_get_chunk_threshold, _set_chunk_threshold)


  def read_messages(self, topics=None, start_time=None, end_time=None):
    if topics and isinstance(topics, str):
      topics = [topics]

    return self._reader.read_messages(topics, start_time, end_time)

  def read_messages_fallback(self, topics=None, start_time=None, end_time=None):
    """
    deprecated
    """
    if topics and isinstance(topics, str):
      topics = [topics]

    return self._reader.read_messages_fallback(topics, start_time, end_time)

  def flush(self):
    if not self._file:
      raise ValueError('I/O operation on closed record')

    # todo(zero): stop writing

  def write(self, topic, msg, t=None, raw=False, proto_descriptor=None):
    if not self._file:
      raise ValueError('I/O operation on closed record')

    if not topic:
      raise ValueError('topic is invalid')
    if not msg:
      raise ValueError('msg is invalid')

    if t is None:
      t = time.time()

    # todo(zero): add write message

  def reindex(self):
    # todo(zero): Reindex, modify chunkinfo and descriptor
    pass

  def close(self):
    if self._file:
      if self._mode in 'wa':
        self._stop_writing()

      self._close_file()

  def get_message_count(self, topic_filters=None):
    message_count = 0

    if topic_filters is not None:
      channel_cache = self._reader.get_channel_cache(topic_filters)
      for channel_info in channel_cache:
        message_count += channel_info.message_number
    else:
      message_count = self._message_number

    return message_count

  def get_start_time(self):
    return self._start_time

  def get_end_time(self):
    return self._end_time

  def set_encryptor(self, encryptor=None, param=None):
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

  def _write_header(self):
    pass

  def _write_index(self):
    """ Add message Index
    """
    pass

  def _write_chunk_header(self):
    pass

  def _write_chunk_body(self):
    pass
