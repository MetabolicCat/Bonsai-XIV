"""The local cache: downloaded sources and the tree built from them."""

import json
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
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

    @contextmanager
    def download(self, source: str, version: str) -> Iterator[Path]:
        """A directory to download `version` of `source` into.

        When the block completes, that version becomes the current one
        and the one it supersedes is removed. When it fails, the
        download is discarded and the current version stays.
        """
        partial = self.directory(source, f"{version}.partial")
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir(parents=True)
        try:
            yield partial
        except BaseException:
            shutil.rmtree(partial)
            raise
        superseded = self.version(source)
        target = self.directory(source, version)
        shutil.rmtree(target, ignore_errors=True)
        partial.rename(target)
        self._set_version(source, version)
        if superseded is not None and superseded != version:
            shutil.rmtree(self.directory(source, superseded))

    def _set_version(self, source: str, version: str) -> None:
        manifest = self._read_manifest()
        manifest[source] = version
        self._manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    def _read_manifest(self) -> dict[str, str]:
        if not self._manifest.exists():
            return {}
        manifest: dict[str, str] = json.loads(self._manifest.read_text())
        return manifest
