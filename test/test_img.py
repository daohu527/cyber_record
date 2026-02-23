import os
import sys
import io
import numpy as np
from PIL import Image
from cyber_record.record import Record


def extract_image_array(proto):
    # proto expected fields: height, width, step, data, encoding (optional)
    data = bytes(proto.data)
    h = int(proto.height)
    w = int(proto.width)
    # step may be width * channels
    step = int(getattr(proto, 'step', w))
    channels = step // w if w != 0 else 1
    arr = np.frombuffer(data, dtype=np.uint8)
    if arr.size != h * step:
        # try with channels=3 fallback
        if arr.size == h * w * 3:
            arr = arr.reshape((h, w, 3))
            return arr
        raise ValueError(f'data size mismatch: {arr.size} != {h}*{step}')
    arr = arr.reshape((h, step))
    if channels > 1:
        arr = arr.reshape((h, w, channels))
    return arr


def compare_images(orig_path, extracted_arr):
    im = Image.open(orig_path).convert('RGB')
    orig_arr = np.asarray(im)
    # If extracted is single channel, convert to 3-channel by stacking
    if extracted_arr.ndim == 2:
        extracted_arr = np.stack([extracted_arr]*3, axis=-1)
    if extracted_arr.shape != orig_arr.shape:
        print(f'Shape mismatch: orig={orig_arr.shape} extracted={extracted_arr.shape}')
        return False
    if np.array_equal(orig_arr, extracted_arr):
        return True
    # allow tiny differences
    return np.allclose(orig_arr, extracted_arr, atol=1)


if __name__ == '__main__':
    base = os.path.dirname(__file__)
    orig_img = os.path.join(base, 'test.jpg')
    # support moved assets in test/assets/
    if not os.path.exists(orig_img):
        orig_img = os.path.join(base, 'assets', 'test.jpg')
    if not os.path.exists(orig_img):
        print('Missing test.jpg')
        sys.exit(1)

    # prefer record produced by test_write_record.py (image -> example_w.record.00002)
    candidates = [
        os.path.join(base, 'example_w.record.00002'),
        os.path.join(base, 'example_w.record.00001'),
        os.path.join(base, 'example_w.record.00000')
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
    r = Record(record_file)
    found = False
    extracted_arr = None
    for topic, message, t in r.read_messages_fallback():
        if 'camera' in topic or 'image' in topic:
            try:
                extracted_arr = extract_image_array(message)
                found = True
                break
            except Exception as e:
                print('Failed to extract image from message:', e)
                continue

    if not found:
        print('No image message found in record')
        sys.exit(3)

    ok = compare_images(orig_img, extracted_arr)
    print('Comparison:', 'MATCH' if ok else 'MISMATCH')
