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
'''cyber_record command implementation'''

from datetime import datetime
import argparse
import sys

from cyber_record.record import Record


kGB = 1 << 30
kMB = 1 << 20
kKB = 1 << 10

def cyber_record_info(record_file):
  if record_file is None:
    print("Usage: cyber_record info -f file")
    return

  record = Record(record_file)
  print("record_file: {}".format(record.filename))
  print("version:     {}".format(record.version))
  print("begin_time:  {}".format(
    datetime.fromtimestamp(record.get_start_time()/1e9)))
  print("end_time:    {}".format(
    datetime.fromtimestamp(record.get_end_time()/1e9)))
  print("duration:    {:.2f} s".format(
    (record.get_end_time() - record.get_start_time())/1e9))

  # size
  if record.size > kGB:
    print("size:        {:.2f} GByte".format(record.size/kGB))
  elif record.size > kMB:
    print("size:        {:.2f} MByte".format(record.size/kMB))
  elif record.size > kKB:
    print("size:        {:.2f} KByte".format(record.size/kKB))
  else:
    print("size:        {:.2f} Byte".format(record.size))

  print("message_number: {}".format(record.get_message_count()))
  print("channel_number: {}".format(len(record.get_channel_cache())))

  # Empty line
  print()
  for channel in record.get_channel_cache():
    print("{:<38}, {:<38}, {}".format(
      channel.name,
      channel.message_type,
      channel.message_number))

def cyber_record_echo(record_file, message_topic):
  if record_file is None or message_topic is None:
    print("Usage: cyber_record echo -f file -t topic")
    return

  record = Record(record_file)
  for topic, message, t in record.read_messages(topics=message_topic):
    print("{}".format(message))

def display_usage():
  print("Usage: cyber_record <command> [<args>]")
  print("The cyber_record commands are:")
  print("\tinfo\tShow information of an exist record.")
  print("\techo\tPrint message to console.")

def main(args=sys.argv):
  if len(args) <= 2:
    display_usage()
    return

  parser = argparse.ArgumentParser(
    description="cyber_record is a cyber record file offline parse tool.",
    prog="main.py")

  parser.add_argument(
    "-f", "--file", action="store", type=str, required=False,
    nargs='?', const="0", help="cyber record file")
  parser.add_argument(
    "-t", "--topic", action="store", type=str, required=False,
    nargs='?', const="0", help="cyber message topic")


  func = args[1]
  args = parser.parse_args(args[2:])
  if func == "info":
    cyber_record_info(args.file)
  elif func == "echo":
    cyber_record_echo(args.file, args.topic)
  else:
    print("Unrecognized parameter type!")
