"""BEV intensity map generator (example)

This is a moved and refactored version of `test/test_bev.py` as an example
under `examples/analysis/`. It reads a PCD (ASCII) and writes a colored
BEV intensity image to `examples/analysis/output/bev_intensity.png`.

Usage:
  python3 examples/analysis/bev_intensity.py [pcd_path]
"""
import os
import numpy as np
import cv2
import sys


def generate_bev_intensity_map(
    pcd_path, out_path, res=0.1, side_range=(-20, 20), fwd_range=(0, 40)
):
    # Load ASCII PCD skipping header until DATA
    data = np.loadtxt(pcd_path, skiprows=11)
    x, y, i = data[:, 0], data[:, 1], data[:, 3]

    mask = (
        (x > fwd_range[0])
        & (x < fwd_range[1])
        & (y > side_range[0])
        & (y < side_range[1])
    )
    x, y, i = x[mask], y[mask], i[mask]

    x_img = (-y / res).astype(np.int32)
    y_img = (-x / res).astype(np.int32)

    x_img -= int(np.floor(side_range[0] / res))
    y_img += int(np.floor(fwd_range[1] / res))

    width = int((side_range[1] - side_range[0]) / res)
    height = int((fwd_range[1] - fwd_range[0]) / res)
    img = np.zeros((height + 1, width + 1), dtype=np.uint8)

    indices = np.argsort(i)
    x_img, y_img, i = x_img[indices], y_img[indices], i[indices]

    keep = (x_img >= 0) & (x_img < width) & (y_img >= 0) & (y_img < height)
    img[y_img[keep], x_img[keep]] = i[keep].astype(np.uint8)

    img_colored = cv2.applyColorMap(img, cv2.COLORMAP_JET)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cv2.imwrite(out_path, img_colored)
    print(f"BEV intensity map generated: {out_path}")


if __name__ == '__main__':
    default_pcd = os.path.join(os.path.dirname(__file__), '../../test/test.pcd')
    pcd = sys.argv[1] if len(sys.argv) > 1 else default_pcd
    out = os.path.join(os.path.dirname(__file__), 'output/bev_intensity.png')
    generate_bev_intensity_map(pcd, out)
