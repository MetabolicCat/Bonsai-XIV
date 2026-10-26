import httpx
import pytest
from upstream import Upstream

from bonsai.cache import Cache
from bonsai.refresh import refresh_game


def refresh(upstream: Upstream, cache: Cache) -> list[str]:
    """Refresh the game data, returning the sources that were downloaded."""
    with upstream.client() as client:
        return refresh_game(client, cache)


def downloads(upstream: Upstream) -> list[str]:
    return [path for path in upstream.requests if path.startswith("raw.")]


def test_a_first_refresh_downloads_every_source(
    upstream: Upstream, cache: Cache
) -> None:
    assert refresh(upstream, cache) == ["datamining", "teamcraft"]


def test_sources_that_did_not_move_are_not_downloaded_again(
    upstream: Upstream, cache: Cache
) -> None:
    refresh(upstream, cache)
    upstream.requests.clear()
    upstream.teamcraft_commit = "e" * 40

    assert refresh(upstream, cache) == ["teamcraft"]
    assert all("teamcraft" in path for path in downloads(upstream))


def test_superseded_versions_are_removed(upstream: Upstream, cache: Cache) -> None:
    refresh(upstream, cache)
    old = upstream.teamcraft_commit
    upstream.teamcraft_commit = "e" * 40

    refresh(upstream, cache)

    assert not [path for path in cache.root.rglob("*") if old in str(path)]


def test_a_failed_download_keeps_the_current_version(
    upstream: Upstream, cache: Cache
) -> None:
    refresh(upstream, cache)
    old = cache.version("teamcraft")
    upstream.teamcraft_commit = "e" * 40
    upstream.failing = True

    with pytest.raises(httpx.HTTPStatusError):
        refresh(upstream, cache)

    assert cache.version("teamcraft") == old
    assert not [path for path in cache.root.rglob("*") if "e" * 40 in str(path)]


def test_downloading_the_current_version_again_replaces_it(cache: Cache) -> None:
    for content in ("first", "second"):
        with cache.download("universalis", "20261026T173553Z") as directory:
            (directory / "market.json").write_text(content)

    current = cache.directory("universalis", "20261026T173553Z")
    assert (current / "market.json").read_text() == "second"
