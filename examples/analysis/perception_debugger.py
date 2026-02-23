"""Perception visualization example (moved from test/test_perception.py)

Usage:
  python3 examples/analysis/perception_debugger.py [record_path]
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from cyber_record.record import Record
import sys
import os


class PerceptionDebugger:
    def __init__(self, record_path):
        self.record_path = record_path
        self.frames = []
        self.current_idx = 0
        self.is_paused = True
        print("Parsing record data...")
        self.load_data()
        self.fig, self.ax = plt.subplots(figsize=(12, 10))
        self.fig.canvas.mpl_connect("key_press_event", self.on_key)

    def load_data(self):
        record = Record(self.record_path)
        for topic, message, t in record.read_messages():
            if topic == "/apollo/perception/obstacles":
                self.frames.append(message)
        print(f"Loaded {len(self.frames)} frames")

    def draw_frame(self, idx):
        self.ax.clear()
        if not self.frames:
            return
        msg = self.frames[idx]
        timestamp = msg.header.timestamp_sec
        for obs in msg.perception_obstacle:
            x, y = obs.position.x, obs.position.y
            l, w, theta = obs.length, obs.width, obs.theta
            cos_t, sin_t = np.cos(theta), np.sin(theta)
            R = np.array([[cos_t, -sin_t], [sin_t, cos_t]])
            local_corners = np.array([[l/2, w/2], [-l/2, w/2], [-l/2, -w/2], [l/2, -w/2]])
            world_corners = (R @ local_corners.T).T + np.array([x, y])
            bbox_poly = patches.Polygon(world_corners, closed=True, linewidth=1.5, edgecolor='red', facecolor='red', alpha=0.2)
            self.ax.add_patch(bbox_poly)
            self.ax.plot(np.append(world_corners[:,0], world_corners[0,0]), np.append(world_corners[:,1], world_corners[0,1]), 'r-', linewidth=1)
            if obs.polygon_point:
                px = [p.x for p in obs.polygon_point]
                py = [p.y for p in obs.polygon_point]
                self.ax.plot(px + [px[0]], py + [py[0]], 'g--', alpha=0.8, linewidth=1)
            self.ax.text(x, y+1, f"ID:{obs.id}", color='blue', fontsize=9, fontweight='bold')
            self.ax.arrow(x, y, cos_t*1.5, sin_t*1.5, head_width=0.4, head_length=0.6, fc='blue', ec='blue')
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle=':', alpha=0.6)
        status_str = 'PAUSED' if self.is_paused else 'PLAYING'
        self.ax.set_title(f"Frame: {idx}/{len(self.frames)-1} | Time: {timestamp:.3f} | [{status_str}]\nSpace: Play/Pause | Left/Right: Step Frame")
        plt.draw()

    def on_key(self, event):
        if event.key == ' ':
            self.is_paused = not self.is_paused
        elif event.key in ['right', 'down']:
            self.current_idx = min(self.current_idx + 1, len(self.frames) - 1)
            self.is_paused = True
        elif event.key in ['left', 'up']:
            self.current_idx = max(self.current_idx - 1, 0)
            self.is_paused = True
        self.draw_frame(self.current_idx)

    def run(self):
        self.draw_frame(self.current_idx)
        while plt.fignum_exists(self.fig.number):
            if not self.is_paused:
                if self.current_idx < len(self.frames) - 1:
                    self.current_idx += 1
                    self.draw_frame(self.current_idx)
                else:
                    self.is_paused = True
                    self.draw_frame(self.current_idx)
            plt.pause(0.1)


if __name__ == '__main__':
    default = os.path.join(os.path.dirname(__file__), '../../test/12-23/20251223151235.record.00000')
    path = sys.argv[1] if len(sys.argv) > 1 else default
    dbg = PerceptionDebugger(path)
    dbg.run()
