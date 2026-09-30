"""data/raw/manifest.json: for each original, where it came from, when, and its SHA-256 hash.

When a file changes upstream, the previous hash is kept in `historial` and the change is reported
(it is never overwritten silently).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gdmty.paths import MANIFEST_FILE


class Manifest:
    def __init__(self, path: Path = MANIFEST_FILE) -> None:
        self.path = path
        self.entries: dict[str, dict[str, Any]] = {}
        if path.exists():
            self.entries = json.loads(path.read_text(encoding="utf-8"))["archivos"]

    def get(self, fid: str) -> dict[str, Any] | None:
        return self.entries.get(fid)

    def record(self, fid: str, entry: dict[str, Any]) -> str:
        """Save an entry; return 'nuevo', 'sin_cambios' or 'modificado'."""
        old = self.entries.get(fid)
        if old is None:
            self.entries[fid] = {**entry, "historial": []}
            return "nuevo"
        if old["sha256"] == entry["sha256"]:
            return "sin_cambios"
        historial = [
            *old.get("historial", []),
            {k: old[k] for k in ("sha256", "descargado", "publicado") if k in old},
        ]
        self.entries[fid] = {**entry, "historial": historial}
        return "modificado"

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"version": 1, "archivos": dict(sorted(self.entries.items()))}
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
