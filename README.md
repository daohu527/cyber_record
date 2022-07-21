# cyber_record

[![Documentation Status](https://readthedocs.org/projects/cyber-record/badge/?version=latest)](https://cyber-record.readthedocs.io/en/latest/?badge=latest)

**[cyber_record](https://cyber-record.readthedocs.io/en/latest/)** is a cyber record file offline parse tool. You can use `cyber_record` to read messages from record file, or write messages to the record file.

## Quick start
First install "cyber_record" by the following command.
```sh
pip3 install cyber_record record_msg
// or update version
pip3 install cyber_record record_msg -U
```

Then you can reference `cyber_record` by
```python
from cyber_record.record import Record
```


## Examples
Below are some examples to help you read and write messages from record files.

## 1. Read messages
You can read messages directly from the record file in the following ways.
```python
from cyber_record.record import Record

file_name = "20210521122747.record.00000"
record = Record(file_name)
for topic, message, t in record.read_messages():
  print("{}, {}, {}".format(topic, type(message), t))
```

The following is the output log of the program
```
/apollo/localization/pose, <class 'LocalizationEstimate'>, 1627031535246897752
/apollo/canbus/chassis, <class 'Chassis'>, 1627031535246913234
/apollo/canbus/chassis, <class 'Chassis'>, 1627031535253680838
```

#### Filter Read
You can also read messages filtered by topics and time. This will improve the speed of parsing messages.
```python
def read_filter_by_both():
  record = Record(file_name)
  for topic, message, t in record.read_messages('/apollo/canbus/chassis', \
      start_time=1627031535164278940, end_time=1627031535215164773):
    print("{}, {}, {}".format(topic, type(message), t))
```


## 2. Parse messages
To avoid introducing too many dependencies, you can save messages by `record_msg`.
```
pip install record_msg
```

`record_msg` provides 3 types of interfaces

#### csv format
you can use `to_csv` to format objects so that they can be easily saved in csv format.
```python
f = open("message.csv", 'w')
writer = csv.writer(f)

def parse_pose(pose):
  '''
  save pose to csv file
  '''
  line = to_csv([pose.header.timestamp_sec, pose.pose])
  writer.writerow(line)

f.close()
```

#### image
you can use `ImageParser` to parse and save images.
```python
image_parser = ImageParser(output_path='../test')
for topic, message, t in record.read_messages():
  if topic == "/apollo/sensor/camera/front_6mm/image":
    image_parser.parse(message)
    # or use timestamp as image file name
    # image_parser.parse(image, t)
```

#### lidar
you can use `PointCloudParser` to parse and save pointclouds.
```python
pointcloud_parser = PointCloudParser('../test')
for topic, message, t in record.read_messages():
  if topic == "/apollo/sensor/lidar32/compensator/PointCloud2":
    pointcloud_parser.parse(message)
    # other modes, default is 'ascii'
    # pointcloud_parser.parse(message, mode='binary')
    # pointcloud_parser.parse(message, mode='binary_compressed')
```


## 3. Write messages
You can now also build record by messages. You can write pb_message by `record.write`.
```python
def write_message():
  pb_map = map_pb2.Map()
  pb_map.header.version = 'hello'.encode()

  with Record(write_file_name, mode='w') as record:
    record.write('/apollo/map', pb_map, int(time.time() * 1e9))
```

Its application scenario is to convert dataset into record files. Please note that it must be written in chronological order.


If you want to write raw message, you should first use `Builder` to help convert raw data to pb_message.

#### image
You can write image to record file like below. `ImageBuilder` will help you convert image to pb_image. `encoding` should be `rgb8`,`bgr8` or `gray`, `y`.
```python
def write_image():
  image_builder = ImageBuilder()
  write_file_name = "example_w.record.00002"
  with Record(write_file_name, mode='w') as record:
    img_path = 'test.jpg'
    pb_image = image_builder.build(img_path, encoding='rgb8')
    record.write('/apollo/sensor/camera/front_6mm/image',
                 pb_image,
                 int(time.time() * 1e9))
```

#### lidar
You can write image to record file like below. `PointCloudBuilder` will help you convert pcd file to pb_point_cloud.
```python
def write_point_cloud():
  point_cloud_builder = PointCloudBuilder()
  write_file_name = "example_w.record.00003"
  with Record(write_file_name, mode='w') as record:
    pcd_path = 'test.pcd'
    pb_point_cloud = point_cloud_builder.build(pcd_path)
    record.write('/apollo/sensor/lidar32/compensator/PointCloud2',
                 pb_point_cloud,
                 int(time.time() * 1e9))
```
