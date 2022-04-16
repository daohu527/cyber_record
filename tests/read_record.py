from cyber_record.record import Record

file_name = "example.record.00000"
record = Record(file_name)
for topic, message, t in record.read_messages():
  print("{}, {}, {}".format(topic, type(message), t))
