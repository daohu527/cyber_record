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

import argparse
import sys
import logging

from datetime import datetime
from google.protobuf import descriptor_pb2

from cyber_record.cyber.proto import record_pb2, proto_desc_pb2
from cyber_record.record import Record


KGB = 1 << 30
KMB = 1 << 20
KKB = 1 << 10


def cyber_record_info(record_file):
    """_summary_

    Args:
        record_file (_type_): _description_
    """
    if record_file is None:
        print("Usage: cyber_record info -f file")
        return

    record = Record(record_file)
    print(f"record_file: {record.filename}")
    print(f"version:     {record.version}")
    print(
        f"begin_time:  {datetime.fromtimestamp(record.get_start_time()/1e9)}")
    print(f"end_time:    {datetime.fromtimestamp(record.get_end_time()/1e9)}")
    print(
        f"duration:    {(record.get_end_time() - record.get_start_time())/1e9:.2f} s")

    # size
    if record.size > KGB:
        print(f"size:        {record.size/KGB:.2f} GByte")
    elif record.size > KMB:
        print(f"size:        {record.size/KMB:.2f} MByte")
    elif record.size > KKB:
        print(f"size:        {record.size/KKB:.2f} KByte")
    else:
        print(f"size:        {record.size:.2f} Byte")

    print(f"message_number: {record.get_message_count()}")
    print(f"channel_number: {len(record.get_channel_cache())}")

    # Empty line
    print()
    for channel in record.get_channel_cache():
        print(
            f"{channel.name:<38}, {channel.message_type:<38}, {channel.message_number}")


def cyber_record_echo(record_file, message_topic):
    """_summary_

    Args:
        record_file (_type_): _description_
        message_topic (_type_): _description_
    """
    if record_file is None or message_topic is None:
        print("Usage: cyber_record echo -f file -t topic")
        return

    record = Record(record_file)
    for _, message, _ in record.read_messages(topics=message_topic):
        print(f"{message}")

# recover cmd


def get_proto_desc(file_desc_proto_dict, proto_file_name, proto_desc):
    """_summary_

    Args:
        file_desc_proto_dict (_type_): _description_
        proto_file_name (_type_): _description_
        proto_desc (_type_): _description_
    """
    file_desc_proto = file_desc_proto_dict[proto_file_name]
    proto_desc.desc = file_desc_proto.SerializeToString()

    for dep_proto_file_name in file_desc_proto.dependency:
        depend = proto_desc.dependencies.add()
        get_proto_desc(file_desc_proto_dict, dep_proto_file_name, depend)


def cyber_record_recover(record_file, desc_file, topic="", msg_type=""):
    """_summary_

    Args:
        record_file (_type_): _description_
        desc_file (_type_): _description_
        topic (str, optional): _description_. Defaults to "".
        msg_type (str, optional): _description_. Defaults to "".
    """
    # 1. read FileDescriptorSet from desc_file
    desc_set = descriptor_pb2.FileDescriptorSet()
    with open(desc_file, 'rb') as f:
        desc_set.ParseFromString(f.read())

    # 2. generate single_index
    file_desc_proto_dict = {}
    for file_desc_proto in desc_set.file:
        logging.debug(file_desc_proto)
        file_desc_proto_dict[file_desc_proto.name] = file_desc_proto

    proto_desc = proto_desc_pb2.ProtoDesc()
    proto_file_name = desc_set.file[-1].name
    get_proto_desc(file_desc_proto_dict, proto_file_name, proto_desc)

    # check msg_type
    package = desc_set.file[-1].package
    msg_types_in_proto = set()
    logging.warning("msg_type should be:")
    for message_type in desc_set.file[-1].message_type:
        msg_types_in_proto.add(f"{package}.{message_type.name}")
        logging.warning(f"\t{package}.{message_type.name}")

    if msg_type and msg_type not in msg_types_in_proto:
        logging.error(f"msg_type must in: {msg_types_in_proto}")
        return

    single_index = record_pb2.SingleIndex()
    single_index.type = record_pb2.SECTION_CHANNEL
    single_index.channel_cache.name = topic
    single_index.channel_cache.message_type = msg_type
    single_index.channel_cache.proto_desc = proto_desc.SerializeToString()

    # 3. recover_index
    with Record(record_file, mode='m') as record:
        record.recover_index(single_index)


def display_usage():
    """_summary_
    """
    print("Usage: cyber_record <command> [<args>]")
    print("The cyber_record commands are:")
    print("\tinfo\tShow information of an exist record.")
    print("\techo\tPrint message to console.")
    print("\trecover\tRecover record file.")


def main(args=sys.argv):
    """_summary_

    Args:
        args (_type_, optional): _description_. Defaults to sys.argv.
    """
    if len(args) <= 2:
        display_usage()
        return

    parser = argparse.ArgumentParser(
        description="cyber_record is a cyber record file offline parse tool.",
        prog="main.py")

    parser.add_argument(
        "-f", "--file", action="store", type=str, required=False,
        nargs='?', const="", help="cyber record file")
    parser.add_argument(
        "-t", "--topic", action="store", type=str, required=False,
        nargs='?', const="", help="cyber message topic")
    parser.add_argument(
        "-m", "--msg_type", action="store", type=str, required=False,
        nargs='?', const="", help="record message type")
    parser.add_argument(
        "-d", "--desc_file", action="store", type=str, required=False,
        nargs='?', const="", help="record message file descriptor")

    func = args[1]
    args = parser.parse_args(args[2:])
    if func == "info":
        cyber_record_info(args.file)
    elif func == "echo":
        cyber_record_echo(args.file, args.topic)
    elif func == "recover":
        if args.topic and args.msg_type:
            cyber_record_recover(args.file, args.desc_file,
                                 args.topic, args.msg_type)
        elif args.topic:
            cyber_record_recover(args.file, args.desc_file, topic=args.topic)
        elif args.msg_type:
            cyber_record_recover(args.file, args.desc_file,
                                 msg_type=args.msg_type)
        else:
            logging.error("Must add topic or msg_type!")
    else:
        logging.error("Unrecognized parameter type!")
