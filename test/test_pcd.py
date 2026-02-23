import os
import io
import sys
import time
import numpy as np
from cyber_record.record import Record


def read_pcd_ascii(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    for i, ln in enumerate(lines):
        if ln.strip().upper().startswith('DATA'):
            data_start = i + 1
            break
    else:
        raise ValueError('No DATA section found in PCD')
    data_text = ''.join(lines[data_start:])
    arr = np.loadtxt(io.StringIO(data_text))
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr


def proto_to_array(proto):
    n = len(proto.point)
    arr = np.zeros((n, 5), dtype=float)
    for i, p in enumerate(proto.point):
        arr[i, 0] = float(p.x)
        arr[i, 1] = float(p.y)
        arr[i, 2] = float(p.z)
        arr[i, 3] = int(p.intensity)
        arr[i, 4] = float(p.timestamp) / 1e9
    return arr


def compare_arrays(orig, extracted):
    if orig.shape[0] != extracted.shape[0]:
        print(f'Row count differs: original={orig.shape[0]} extracted={extracted.shape[0]}')
        return False
    if not np.allclose(orig[:, :3], extracted[:, :3], atol=1e-6):
        dif = np.abs(orig[:, :3] - extracted[:, :3])
        idx = np.unravel_index(np.argmax(dif), dif.shape)[0]
        print(f'XYZ mismatch at row {idx}: orig={orig[idx,:3]} ext={extracted[idx,:3]}')
        return False
    if not np.array_equal(orig[:, 3].astype(int), extracted[:, 3].astype(int)):
        for i in range(orig.shape[0]):
            if int(orig[i, 3]) != int(extracted[i, 3]):
                print(f'Intensity mismatch at {i}: {int(orig[i,3])} != {int(extracted[i,3])}')
                break
        return False
    orig_ns = (orig[:, 4].astype(float) * 1e9).astype(np.int64)
    ext_ns = (extracted[:, 4].astype(float) * 1e9).astype(np.int64)
    if np.max(np.abs(orig_ns - ext_ns)) > 1000:
        idx = int(np.argmax(np.abs(orig_ns - ext_ns)))
        print(f'Timestamp mismatch at {idx}: orig={orig_ns[idx]} ns ext={ext_ns[idx]} ns')
        return False
    return True


if __name__ == '__main__':
    base_dir = os.path.dirname(__file__)
    pcd_path = os.path.join(base_dir, 'test.pcd')
    # fall back to assets/ for permanent test assets
    if not os.path.exists(pcd_path):
        pcd_path = os.path.join(base_dir, 'assets', 'test.pcd')
    if not os.path.exists(pcd_path):
        print('Missing test.pcd')
        sys.exit(1)

    candidates = [
        os.path.join(base_dir, 'example_w.record.00003'),
        os.path.join(base_dir, 'example_pcd.record.00000'),
        os.path.join(base_dir, 'assets', 'example_pcd.record.00000'),
    ]
    record_file = None
    for c in candidates:
        if os.path.exists(c):
            record_file = c
            break
    if len(sys.argv) > 1:
        record_file = sys.argv[1]
    if record_file is None:
        print('No record file found. Run test/test_write_record.py first.')
        sys.exit(2)

    print(f'Using record: {record_file}')

    orig = read_pcd_ascii(pcd_path)
    print(f'Original PCD rows: {orig.shape[0]}')

    r = Record(record_file)
    extracted_proto = None
    for topic, message, t in r.read_messages_fallback():
        if 'PointCloud' in topic or 'PointCloud2' in topic:
            extracted_proto = message
            break

    if extracted_proto is None:
        print('No pointcloud message found in record')
        sys.exit(3)

    extracted = proto_to_array(extracted_proto)
    print(f'Extracted rows: {extracted.shape[0]}')

    ok = compare_arrays(orig, extracted)
    print('Comparison:', 'MATCH' if ok else 'MISMATCH')
