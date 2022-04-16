# cyber_record
Cyber record file offline parse tool. You can use `cyber_record` to read messages from record file, or write messages to the record file.

## Quick start
First install "cyber_record" by the following command.
```
pip install cyber_record
// or update version
pip install cyber_record -U
```

Then you can reference `cyber_record` by
```python
from cyber_record.record import Record
```


## Examples
Below are some examples to help you read and write messages from record files.

#### Read messages
You can read messages directly from the record file in the following ways.
```python
from cyber_record.record import Record


file_name = "20210521122747.record.00000"
record = Record(file_name)
for topic, message, t in record.read_messages():
  print("{}, {}, {}".format(topic, message, t))
```

You can also find the read record example directly in the tests directory
```
cd tests/
python3 read_record.py
```

The following is the output log of the program
```
/apollo/localization/pose, <class 'LocalizationEstimate'>, 1627031535246897752
/apollo/canbus/chassis, <class 'Chassis'>, 1627031535246913234
/apollo/canbus/chassis, <class 'Chassis'>, 1627031535253680838
```
