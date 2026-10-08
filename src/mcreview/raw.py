"""Content-addressed store for raw HTTP response bodies.

Files live at <raw>/<sha256[:2]>/<sha256>.<ext>.gz and are never modified once written,
so the database can be re-derived from them without re-fetching.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path


class RawStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def put(self, content: bytes, ext: str = "json") -> str:
        sha = hashlib.sha256(content).hexdigest()
        path = self._path(sha, ext)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            with gzip.open(tmp, "wb", compresslevel=6) as f:
                f.write(content)
            tmp.replace(path)
        return f"{sha}.{ext}"

    def get(self, ref: str) -> bytes:
        sha, ext = ref.split(".", 1)
        with gzip.open(self._path(sha, ext), "rb") as f:
            return f.read()

    def _path(self, sha: str, ext: str) -> Path:
        return self.root / sha[:2] / f"{sha}.{ext}.gz"
