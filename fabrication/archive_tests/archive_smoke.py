"""
archive_smoke.py  (fabrication/archive_tests/)

Build an archive of the framework, then verify it round-trips:
every file's SHA-256 in the manifest must match every file
extracted from the archive.

Discovers the real repo root from the archive module's location
because the smoke runner gives each test its own tempfile.mkdtemp()
working directory.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.archive_tests.archive_smoke

License: CC0. Stdlib only.
"""
import sys
import tempfile
from pathlib import Path

from .. import archive


def main():
    # archive lives at <repo_root>/fabrication/archive.py
    # so .parent.parent == repo root.
    repo_root = Path(archive.__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        result = archive.snapshot(root=str(repo_root), out_dir=tmp)
        print(f"  wrote {result['tar']}")
        print(f"  wrote {result['zip']}")
        print(f"  wrote {result['manifest']}")
        print(f"  file count:  {result['file_count']}")
        print(f"  total bytes: {result['total_bytes']:,}")

        v_tar = archive.verify_archive(result["tar"])
        v_zip = archive.verify_archive(result["zip"])
        print(f"  tar verify: "
              f"{'OK' if v_tar['ok'] else 'FAIL'} "
              f"({v_tar.get('n_files')} files, "
              f"{v_tar.get('n_failed')} failed)")
        print(f"  zip verify: "
              f"{'OK' if v_zip['ok'] else 'FAIL'} "
              f"({v_zip.get('n_files')} files, "
              f"{v_zip.get('n_failed')} failed)")
        assert v_tar["ok"], v_tar
        assert v_zip["ok"], v_zip
    print("archive smoke OK")


if __name__ == "__main__":
    sys.exit(main() or 0)
