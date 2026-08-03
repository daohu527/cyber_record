from PIL import Image
from wheelos_msgs.sensor_msgs import pointcloud_pb2, sensor_image_pb2

from cyber_record.message_tools import (
    ImageBuilder,
    ImageParser,
    PointCloudBuilder,
    PointCloudParser,
    to_csv,
)


def test_image_builder_and_parser_without_opencv(tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (2, 1), (255, 0, 32)).save(source)

    message = ImageBuilder(sensor_image_pb2.Image).build(
        source, frame_id="camera", encoding="rgb8", t=12.5
    )
    assert message.width == 2
    assert message.data == bytes((255, 0, 32, 255, 0, 32))

    output = tmp_path / "images"
    parsed = ImageParser(output).parse(message)
    assert parsed.size == (2, 1)
    assert Image.open(output / "00000.jpg").size == (2, 1)


def test_pointcloud_builder_and_parser(tmp_path):
    source = tmp_path / "source.pcd"
    source.write_text(
        "VERSION 0.7\n"
        "FIELDS x y z intensity timestamp\n"
        "SIZE 4 4 4 4 8\n"
        "TYPE F F F U F\n"
        "COUNT 1 1 1 1 1\n"
        "WIDTH 1\nHEIGHT 1\n"
        "VIEWPOINT 0 0 0 1 0 0 0\n"
        "POINTS 1\nDATA ascii\n"
        "1 2 3 4 5.5\n",
        encoding="ascii",
    )

    message = PointCloudBuilder(pointcloud_pb2.PointCloud).build(
        source, frame_id="lidar", t=12.5
    )
    assert len(message.point) == 1
    assert message.point[0].timestamp == 5500000000

    output = tmp_path / "clouds"
    data = PointCloudParser(output).parse(message)
    assert data[0]["intensity"] == 4
    assert (output / "00000.pcd").exists()


def test_to_csv_flattens_protobuf_message():
    message = pointcloud_pb2.PointCloud(width=1, height=1)
    message.point.add(x=1, y=2, z=3, intensity=4, timestamp=5)
    values = to_csv(message)
    assert 1 in values
    assert 4 in values
