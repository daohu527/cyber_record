Examples (data analysis)
=========================

This folder contains interactive examples and analysis scripts derived from
tests. They are not unit tests, but runnable examples for data exploration.

Structure
- `bev_intensity.py` - generate BEV intensity image from a PCD.
- `intensity_analysis.py` - visualize intensity distribution and mappings.
- `pose_analysis.py` - load poses from record files and plot trajectory.
- `perception_debugger.py` - interactive perception frame inspector.

Data assets
----------
Place canonical small test assets in `test/assets/` (recommended). To move
current `test/test.pcd` and `test/test.jpg` into that directory run:

```sh
python3 tools/move_test_assets.py
```

Cleanup
-------
To remove intermediate generated records and outputs created by the examples:

```sh
python3 tools/cleanup_generated.py
```
