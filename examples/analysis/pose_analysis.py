"""Pose analysis example (moved from test/test_pose.py)

Usage:
  python3 examples/analysis/pose_analysis.py [poses_directory]
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from cyber_record.record import Record


def parse_pose(msg):
    header_timestamp_sec = msg.header.timestamp_sec
    pose = msg.pose
    return {
        "timestamp": header_timestamp_sec,
        "position": (pose.position.x, pose.position.y),
        "orientation": (pose.orientation.qx, pose.orientation.qy, pose.orientation.qz, pose.orientation.qw),
        "heading": pose.heading,
    }


def read_poses_from_directory(directory_path):
    poses = []
    file_paths = sorted(os.listdir(directory_path))
    for filename in file_paths:
        file_path = os.path.join(directory_path, filename)
        record = Record(file_path)
        for topic, message, t in record.read_messages_fallback():
            if topic == "/apollo/localization/pose":
                pose = parse_pose(message)
                poses.append(pose)
    return poses


def evaluate_localization(poses):
    if not poses:
        return None
    positions = np.array([pose["position"] for pose in poses])
    timestamps = np.array([pose["timestamp"] for pose in poses])
    distances = np.linalg.norm(positions[1:] - positions[:-1], axis=1)
    headings = [pose["heading"] for pose in poses]
    return timestamps, positions, headings, distances


def plot_trajectory_and_errors(timestamps, positions, headings, distances):
    fig, axs = plt.subplots(3, 1, figsize=(10, 12))
    axs[0].plot(positions[:, 0], positions[:, 1], color="blue", linewidth=0.5)
    axs[0].scatter(positions[:, 0], positions[:, 1], color="blue", s=10)
    axs[0].set_title("Trajectory")
    axs[1].plot(timestamps, headings, color="green", linewidth=0.5)
    axs[1].set_title("Heading vs Time")
    axs[2].plot(timestamps[1:], distances, color="red", linewidth=0.5)
    axs[2].set_title("Inter-frame distances")
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    default_dir = os.path.join(os.path.dirname(__file__), '../../test/slam')
    poses_dir = sys.argv[1] if len(sys.argv) > 1 else default_dir
    poses = read_poses_from_directory(poses_dir)
    results = evaluate_localization(poses)
    if results:
        timestamps, positions, headings, distances = results
        print(f"Total poses: {len(positions)}")
        plot_trajectory_and_errors(timestamps, positions, headings, distances)
    else:
        print('No poses found')
