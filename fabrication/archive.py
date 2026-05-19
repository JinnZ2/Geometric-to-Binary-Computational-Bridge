"""
archive.py  (fabrication/)

Snapshot the framework into a single CC0 deliverable. Stdlib
only -- no git, no network, no pip.

Three artifacts per snapshot, written in parallel:

  fabrication-bridge-<TS>.tar.gz       full source + docs
  fabrication-bridge-<TS>.zip          same content, ZIP form
  fabrication-bridge-<TS>.MANIFEST.json file list + SHA-256 +
                                       embedded framework state

Verification:
  verify_archive(<path>)
  walks the manifest and confirms each archived file's SHA-256
  matches its manifest entry. End-to-end tamper check.

CLI:
  python -m fabrication.archive snapshot [out_dir]
  python -m fabrication.archive verify <archive_path>

License: CC0. Stdlib only.
"""
import hashlib
import io
import json
import os
import sys
import tarfile
import time
import zipfile
from pathlib import Path


INCLUDE_DIRS  = ["fabrication"]
INCLUDE_FILES = ["README.md", "ARCHITECTURE.md", "LICENSE"]

EXCLUDE_DIRS = {"__pycache__", ".git", ".mypy_cache",
                ".pytest_cache", "_emit_out", "node_modules"}
EXCLUDE_EXT  = {".pyc", ".pyo", ".so", ".dylib"}


def _iter_files(root):
    """Yield Path objects for every file we want to archive."""
    for base in INCLUDE_DIRS:
        p = root / base
        if not p.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames
                           if d not in EXCLUDE_DIRS]
            for f in filenames:
                if Path(f).suffix in EXCLUDE_EXT:
                    continue
                yield Path(dirpath) / f
    for f in INCLUDE_FILES:
        p = root / f
        if p.exists():
            yield p


def _sha256(path, chunk=65536):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            buf = fh.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()


def build_manifest(root):
    root = Path(root)
    files = []
    for p in _iter_files(root):
        rel = p.relative_to(root).as_posix()
        files.append({
            "path":   rel,
            "size":   p.stat().st_size,
            "sha256": _sha256(p),
        })
    # embed framework state from the live ledger if present
    state = {}
    ledger_path = root / "CLAIM_TABLE.fab.json"
    if ledger_path.exists():
        try:
            ledger = json.loads(ledger_path.read_text())
            state["n_claims_in_ledger"] = len(ledger)
            domains = {}
            for c in ledger:
                parts = c.get("scope", "").split("::")
                if len(parts) >= 2 and parts[0] == "fab":
                    domains[parts[1]] = domains.get(parts[1], 0) + 1
            state["claims_by_domain"] = domains
        except Exception:
            pass
    return {
        "framework":    "geometric-to-binary computational bridge",
        "subsystem":    "fabrication",
        "license":      "CC0",
        "snapshot_ts":  time.time(),
        "snapshot_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                      time.gmtime()),
        "python_min":   "3.10",
        "dependencies": "stdlib only",
        "file_count":   len(files),
        "total_bytes":  sum(f["size"] for f in files),
        "state":        state,
        "files":        files,
    }


def write_tar(root, out_path, manifest):
    with tarfile.open(out_path, "w:gz") as tf:
        for f in manifest["files"]:
            src = Path(root) / f["path"]
            tf.add(src, arcname=f"bridge/{f['path']}")
        man_bytes = json.dumps(manifest, indent=2,
                               default=str).encode()
        info = tarfile.TarInfo(name="bridge/MANIFEST.json")
        info.size = len(man_bytes)
        info.mtime = int(time.time())
        tf.addfile(info, io.BytesIO(man_bytes))
    return out_path


def write_zip(root, out_path, manifest):
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in manifest["files"]:
            src = Path(root) / f["path"]
            zf.write(src, arcname=f"bridge/{f['path']}")
        zf.writestr("bridge/MANIFEST.json",
                    json.dumps(manifest, indent=2, default=str))
    return out_path


def snapshot(root=".", out_dir="."):
    root = Path(root).resolve()
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(exist_ok=True, parents=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    base = f"fabrication-bridge-{stamp}"

    manifest = build_manifest(root)
    tar_path = out_dir / f"{base}.tar.gz"
    zip_path = out_dir / f"{base}.zip"
    man_path = out_dir / f"{base}.MANIFEST.json"

    write_tar(root, tar_path, manifest)
    write_zip(root, zip_path, manifest)
    man_path.write_text(json.dumps(manifest, indent=2,
                                   default=str))

    return {
        "tar":          str(tar_path),
        "zip":          str(zip_path),
        "manifest":     str(man_path),
        "file_count":   manifest["file_count"],
        "total_bytes":  manifest["total_bytes"],
        "snapshot_iso": manifest["snapshot_iso"],
    }


def verify_archive(archive_path):
    """Open .tar.gz or .zip and confirm every file's SHA-256
    matches its manifest entry."""
    path = Path(archive_path)
    if str(path).endswith(".tar.gz") or path.suffix == ".tgz":
        return _verify_tar(path)
    if path.suffix == ".zip":
        return _verify_zip(path)
    raise ValueError(f"Unknown archive type: {path}")


def _verify_tar(path):
    results = []
    with tarfile.open(path, "r:gz") as tf:
        manifest = None
        for n in tf.getnames():
            if n.endswith("MANIFEST.json"):
                fh = tf.extractfile(n)
                manifest = json.loads(fh.read().decode())
                break
        if manifest is None:
            return {"ok": False,
                    "error": "no MANIFEST.json in archive"}
        for f in manifest["files"]:
            arc = f"bridge/{f['path']}"
            try:
                content = tf.extractfile(arc).read()
                actual = hashlib.sha256(content).hexdigest()
                ok = (actual == f["sha256"])
                results.append({
                    "path": f["path"], "ok": ok,
                    "expected": f["sha256"], "actual": actual,
                })
            except Exception as e:
                results.append({"path": f["path"], "ok": False,
                                "error": str(e)})
    return {
        "ok":        all(r["ok"] for r in results),
        "n_files":   len(results),
        "n_failed":  sum(1 for r in results if not r["ok"]),
        "results":   results,
    }


def _verify_zip(path):
    results = []
    with zipfile.ZipFile(path, "r") as zf:
        manifest = None
        for n in zf.namelist():
            if n.endswith("MANIFEST.json"):
                manifest = json.loads(zf.read(n).decode())
                break
        if manifest is None:
            return {"ok": False,
                    "error": "no MANIFEST.json in archive"}
        for f in manifest["files"]:
            arc = f"bridge/{f['path']}"
            try:
                content = zf.read(arc)
                actual = hashlib.sha256(content).hexdigest()
                ok = (actual == f["sha256"])
                results.append({
                    "path": f["path"], "ok": ok,
                    "expected": f["sha256"], "actual": actual,
                })
            except Exception as e:
                results.append({"path": f["path"], "ok": False,
                                "error": str(e)})
    return {
        "ok":        all(r["ok"] for r in results),
        "n_files":   len(results),
        "n_failed":  sum(1 for r in results if not r["ok"]),
        "results":   results,
    }


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: archive snapshot [out_dir] "
              "| archive verify <path>")
        return 0
    cmd = argv[0]
    if cmd == "snapshot":
        out = argv[1] if len(argv) > 1 else "."
        result = snapshot(out_dir=out)
        print(json.dumps(result, indent=2, default=str))
        return 0
    if cmd == "verify":
        if len(argv) < 2:
            print("verify needs an archive path"); return 2
        result = verify_archive(argv[1])
        print(f"  files checked: {result.get('n_files','?')}")
        print(f"  failures:      {result.get('n_failed','?')}")
        ok = result.get("ok")
        print(f"  verdict:       {'OK' if ok else 'FAIL'}")
        return 0 if ok else 1
    print(f"unknown cmd: {cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
