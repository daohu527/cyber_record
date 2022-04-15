# cyber_record
cyber_record offline parse tool. With cyber_record you can read and write messages from the record file.


## read record
You can directly read the record file in the following way.

```python
from cyber_record.record import Record

file_name = "20210521122747.record.00000"
record = Record(file_name)
for topic, message, t in record.read_messages():
  print("{}, {}, {}".format(topic, message, t))
```