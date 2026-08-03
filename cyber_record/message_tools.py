"""Optional helpers for converting protobuf image and point-cloud messages.

The core record reader does not import this module. Install the ``msg-tools``
extra when image or point-cloud conversion is needed.
"""

import importlib
import struct
from collections.abc import Iterable
from pathlib import Path


def _numpy():
    try:
        return importlib.import_module("numpy")
    except ImportError as err:
        raise ImportError(
            "message tools require numpy; install cyber_record[msg-tools]"
        ) from err


def _pillow():
    try:
        return importlib.import_module("PIL.Image")
    except ImportError as err:
        raise ImportError(
            "image tools require Pillow; install cyber_record[msg-tools]"
        ) from err


def _default_message(module_name, type_name):
    try:
        module = importlib.import_module(module_name)
        return getattr(module, type_name)
    except (ImportError, AttributeError) as err:
        raise ImportError(
            f"{type_name} is unavailable; pass message_type explicitly or "
            "install cyber_record[msgs]"
        ) from err


def to_csv(value):
    """Flatten scalars, sequences, and protobuf messages into CSV values."""
    if isinstance(value, (int, float, bool, str, bytes)):
        return [value]
    if isinstance(value, (tuple, list)):
        result = []
        for item in value:
            result.extend(to_csv(item))
        return result
    if hasattr(value, "DESCRIPTOR"):
        result = []
        for field in value.DESCRIPTOR.fields:
            result.extend(to_csv(getattr(value, field.name)))
        return result
    if isinstance(value, Iterable):
        result = []
        for item in value:
            result.extend(to_csv(item))
        return result
    return []


class ImageParser:
    """Convert an image protobuf message to an image file without OpenCV."""

    def __init__(self, output_path, instance_saving=True, suffix=".jpg"):
        self.output_path = Path(output_path)
        self.instance_saving = instance_saving
        self.suffix = suffix
        self._message_count = 0

    def parse(self, image, file_name=None):
        channels = {"rgb8": 3, "bgr8": 3, "gray": 1, "y": 1}.get(
            image.encoding
        )
        if channels is None or image.step != image.width * channels:
            raise ValueError(f"unsupported image format: {image.encoding}")
        image_module = _pillow()
        mode = "L" if channels == 1 else "RGB"
        data = bytes(image.data)
        if channels == 3 and image.encoding == "bgr8":
            array = _numpy().frombuffer(data, dtype=_numpy().uint8).reshape(
                image.height, image.width, 3
            )
            data = array[:, :, ::-1].tobytes()
        result = image_module.frombytes(mode, (image.width, image.height), data)
        if self.instance_saving:
            name = (
                f"{self._message_count:05d}{self.suffix}"
                if file_name is None
                else f"{file_name}{self.suffix}"
            )
            self.output_path.mkdir(parents=True, exist_ok=True)
            result.save(self.output_path / name)
            self._message_count += 1
        return result


def _pcd_dtype(fields, sizes, types, counts):
    numpy = _numpy()
    type_map = {
        ("F", 4): numpy.float32,
        ("F", 8): numpy.float64,
        ("I", 1): numpy.int8,
        ("I", 2): numpy.int16,
        ("I", 4): numpy.int32,
        ("I", 8): numpy.int64,
        ("U", 1): numpy.uint8,
        ("U", 2): numpy.uint16,
        ("U", 4): numpy.uint32,
        ("U", 8): numpy.uint64,
    }
    dtype = []
    for field, size, kind, count in zip(fields, sizes, types, counts):
        try:
            item_type = type_map[(kind, size)]
        except KeyError as err:
            raise ValueError(f"unsupported PCD field type: {kind}{size}") from err
        dtype.append((field, item_type, count) if count != 1 else (field, item_type))
    return numpy.dtype(dtype)


def _read_pcd(path):
    header = {}
    with open(path, "rb") as stream:
        while True:
            line = stream.readline()
            if not line:
                raise ValueError("PCD header is incomplete")
            text = line.decode("ascii").strip()
            if text and not text.startswith("#"):
                key, *values = text.split()
                header[key.upper()] = values
            if text.upper().startswith("DATA "):
                break
        fields = header["FIELDS"]
        sizes = list(map(int, header["SIZE"]))
        types = header["TYPE"]
        counts = list(map(int, header.get("COUNT", ["1"] * len(fields))))
        dtype = _pcd_dtype(fields, sizes, types, counts)
        points = int(header["POINTS"][0])
        data_type = header["DATA"][0].lower()
        if data_type == "ascii":
            rows = []
            for _ in range(points):
                rows.append(stream.readline().decode("ascii").split())
            data = _numpy().array(rows, dtype=_numpy().float64)
            result = _numpy().empty(points, dtype=dtype)
            for index, field in enumerate(fields):
                result[field] = data[:, index]
            return header, result
        if data_type == "binary":
            return header, _numpy().frombuffer(
                stream.read(points * dtype.itemsize), dtype=dtype, count=points
            )
        if data_type == "binary_compressed":
            compressed_size, uncompressed_size = struct.unpack(
                "<II", stream.read(8)
            )
            try:
                lzf = importlib.import_module("lzf")
            except ImportError as err:
                raise ImportError(
                    "compressed PCD requires python-lzf; install "
                    "cyber_record[msg-tools]"
                ) from err
            raw = lzf.decompress(stream.read(compressed_size), uncompressed_size)
            if raw is None:
                raise ValueError("invalid compressed PCD payload")
            return header, _numpy().frombuffer(raw, dtype=dtype, count=points)
        raise ValueError(f"unsupported PCD data format: {data_type}")


class PointCloudParser:
    """Convert a PointCloud protobuf message to an ASCII PCD file."""

    def __init__(self, output_path, instance_saving=True, suffix=".pcd"):
        self.output_path = Path(output_path)
        self.instance_saving = instance_saving
        self.suffix = suffix
        self._message_count = 0

    def parse(self, pointcloud, file_name=None, mode="ascii"):
        if mode != "ascii":
            raise ValueError("PointCloudParser currently supports ASCII output")
        numpy = _numpy()
        points = pointcloud.point
        if self.instance_saving:
            name = (
                f"{self._message_count:05d}{self.suffix}"
                if file_name is None
                else f"{file_name}{self.suffix}"
            )
            self.output_path.mkdir(parents=True, exist_ok=True)
            path = self.output_path / name
            with path.open("w", encoding="ascii") as stream:
                stream.write(
                    "VERSION 0.7\nFIELDS x y z intensity timestamp\n"
                    "SIZE 4 4 4 4 8\nTYPE F F F U F\nCOUNT 1 1 1 1 1\n"
                    f"WIDTH {len(points)}\nHEIGHT 1\n"
                    "VIEWPOINT 0 0 0 1 0 0 0\n"
                    f"POINTS {len(points)}\nDATA ascii\n"
                )
                for point in points:
                    stream.write(
                        f"{point.x} {point.y} {point.z} {point.intensity} "
                        f"{point.timestamp / 1e9}\n"
                    )
            self._message_count += 1
        return numpy.array(
            [(p.x, p.y, p.z, p.intensity, p.timestamp / 1e9) for p in points],
            dtype=[("x", "f4"), ("y", "f4"), ("z", "f4"),
                   ("intensity", "u4"), ("timestamp", "f8")],
        )


class ImageBuilder:
    """Build an image protobuf message using Pillow."""

    def __init__(self, message_type=None):
        self.message_type = message_type or _default_message(
            "wheelos_msgs.sensor_msgs.sensor_image_pb2", "Image"
        )
        self._sequence_num = 0

    def build(self, file_name, frame_id, encoding, t=None):
        image_module = _pillow()
        image = image_module.open(file_name)
        if encoding == "rgb8":
            image = image.convert("RGB")
            data = image.tobytes()
            step = image.width * 3
        elif encoding == "bgr8":
            image = image.convert("RGB")
            data = bytes(bytearray(image.tobytes())[index]
                         for pixel in range(image.width * image.height)
                         for index in (pixel * 3 + 2, pixel * 3 + 1,
                                       pixel * 3))
            step = image.width * 3
        elif encoding in ("gray", "y"):
            image = image.convert("L")
            data = image.tobytes()
            step = image.width
        else:
            raise ValueError(f"unsupported image encoding: {encoding}")
        message = self.message_type(
            frame_id=frame_id,
            measurement_time=t or 0,
            height=image.height,
            width=image.width,
            encoding=encoding,
            step=step,
            data=data,
        )
        if hasattr(message, "header"):
            message.header.sequence_num = self._sequence_num
            message.header.frame_id = frame_id
            if t is not None:
                message.header.timestamp_sec = t
        self._sequence_num += 1
        return message


class PointCloudBuilder:
    """Build a PointCloud protobuf message from an ASCII or binary PCD file."""

    def __init__(self, message_type=None):
        self.message_type = message_type or _default_message(
            "wheelos_msgs.sensor_msgs.pointcloud_pb2", "PointCloud"
        )
        self._sequence_num = 0

    def build(self, file_name, frame_id, t=None):
        header, data = _read_pcd(file_name)
        fields = set(data.dtype.names or ())
        required = {"x", "y", "z", "intensity"}
        if not required.issubset(fields):
            raise ValueError("PCD must contain x, y, z, and intensity fields")
        message = self.message_type(
            frame_id=frame_id,
            measurement_time=t or 0,
            width=int(header["WIDTH"][0]),
            height=int(header["HEIGHT"][0]),
        )
        if hasattr(message, "header"):
            message.header.sequence_num = self._sequence_num
            message.header.frame_id = frame_id
            if t is not None:
                message.header.timestamp_sec = t
        for row in data:
            point = message.point.add(
                x=float(row["x"]),
                y=float(row["y"]),
                z=float(row["z"]),
                intensity=int(row["intensity"]),
            )
            if "timestamp" in fields:
                point.timestamp = int(float(row["timestamp"]) * 1e9)
        self._sequence_num += 1
        return message


__all__ = [
    "ImageBuilder",
    "ImageParser",
    "PointCloudBuilder",
    "PointCloudParser",
    "to_csv",
]
