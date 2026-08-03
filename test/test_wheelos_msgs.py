from wheelos_msgs.map_msgs import map_pb2

from cyber_record.record import Record


def test_wheelos_message_round_trip(tmp_path):
    path = tmp_path / "map.record.00000"
    message = map_pb2.Map()
    message.header.version = b"wheelos-msgs"

    with Record(str(path), mode="w") as record:
        record.write("/apollo/map", message, 1)

    with Record(str(path)) as record:
        topic, restored, timestamp = next(record.read_messages())

    assert topic == "/apollo/map"
    assert timestamp == 1
    assert restored.SerializeToString() == message.SerializeToString()
