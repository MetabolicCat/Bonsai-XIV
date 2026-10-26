"""The local cache: downloaded sources and the tree built from them."""

import json
from pathlib import Path


class Cache:
    """A cache directory.

    `sources/<source>/<version>/` holds the files of a source as they
    were downloaded; `sources/manifest.json` records which version of
    each source is current. `bonsai.sqlite` is the tree built from them.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.database = root / "bonsai.sqlite"
        self._sources = root / "sources"
        self._manifest = self._sources / "manifest.json"

    def directory(self, source: str, version: str) -> Path:
        return self._sources / source / version

    def version(self, source: str) -> str | None:
        version: str | None = self._read_manifest().get(source)
        return version

    def set_version(self, source: str, version: str) -> None:
        manifest = self._read_manifest()
        manifest[source] = version
        self._manifest.parent.mkdir(parents=True, exist_ok=True)
        self._manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    def _read_manifest(self) -> dict[str, str]:
        if not self._manifest.exists():
            return {}
        manifest: dict[str, str] = json.loads(self._manifest.read_text())
        return manifest
