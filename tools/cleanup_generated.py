#!/usr/bin/env python3
"""Cleanup generated intermediate files created by examples/tests."""
import shutil
import pathlib
import sys


def main():
    repo = pathlib.Path(__file__).resolve().parent.parent
    removed = []

    # Remove example_* record files in test/ and test/assets/
    candidates = list(repo.glob('test/example_*.record.*'))
    candidates += list(repo.glob('test/assets/example_*.record.*'))
    candidates += list(repo.glob('test/assets/example.record.*'))
    for p in candidates:
        # Do not remove the canonical example.record.00000 (preserve original)
        if p.name == 'example.record.00000':
            continue
        try:
            if p.exists():
                p.unlink()
                removed.append(str(p))
        except Exception:
            pass

    # Remove test/pcd_output/ if present
    pcd_out = repo / 'test' / 'pcd_output'
    if pcd_out.exists():
        try:
            shutil.rmtree(pcd_out)
            removed.append(str(pcd_out))
        except Exception:
            pass

    # Remove examples/analysis/output/ if present
    ex_out = repo / 'examples' / 'analysis' / 'output'
    if ex_out.exists():
        try:
            shutil.rmtree(ex_out)
            removed.append(str(ex_out))
        except Exception:
            pass

    # Optionally remove any other large generated files under test/ matching patterns
    for p in repo.glob('test/*.pcd_output*'):
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            removed.append(str(p))
        except Exception:
            pass

    if removed:
        print('Removed:')
        for r in removed:
            print(' -', r)
        sys.exit(0)
    else:
        print('No generated files found')
        sys.exit(0)


if __name__ == '__main__':
    main()
