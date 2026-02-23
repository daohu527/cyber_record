"""Intensity analysis example (moved from test/test_intensity.py)

Usage:
  python3 examples/analysis/intensity_analysis.py [pcd_path]
"""
import numpy as np
import matplotlib.pyplot as plt
import sys
import os


def sigmoid_convert(x, x0, k, upper_limit=255):
    res = upper_limit / (1 + np.exp(-k * (x - x0)))
    return np.clip(res, 0, upper_limit).astype(np.uint8)


def analyze_intensity_and_mapping(pcd_path):
    data = np.loadtxt(pcd_path, skiprows=11)
    intensity = data[:, 3]
    print(f"Max: {np.max(intensity):.2f} Min: {np.min(intensity):.2f} Mean: {np.mean(intensity):.2f}")
    p25, p75, p90 = np.percentile(intensity, [25, 75, 90])
    print(f"25%: {p25:.2f} 90%: {p90:.2f}")
    conf_a = (15.0, 0.35)
    conf_b = (10.0, 0.45)
    mapped_a = sigmoid_convert(intensity, *conf_a)
    mapped_b = sigmoid_convert(intensity, *conf_b)
    fig, axes = plt.subplots(1, 2, figsize=(15,5))
    axes[0].hist(intensity, bins=100, color='gray', alpha=0.7)
    axes[0].set_yscale('log')
    axes[1].hist(mapped_a, bins=50, alpha=0.5, label='Conf A', color='red')
    axes[1].hist(mapped_b, bins=50, alpha=0.5, label='Conf B', color='green')
    axes[1].legend()
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    default = os.path.join(os.path.dirname(__file__), '../../test/test.pcd')
    pcd = sys.argv[1] if len(sys.argv) > 1 else default
    analyze_intensity_and_mapping(pcd)
