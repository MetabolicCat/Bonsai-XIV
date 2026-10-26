from pathlib import Path

import pytest
from upstream import Upstream

from bonsai.__main__ import main


@pytest.fixture
def upstream() -> Upstream:
    upstream = Upstream()
    upstream.sheets["Item"] = [{"#": 5057, "Name": "Iron Ingot"}]
    return upstream


def run(upstream: Upstream, cache: Path, *args: str) -> int:
    with upstream.client() as client:
        return main(["--cache-dir", str(cache), *args], client=client)


def test_status_of_an_empty_cache(
    tmp_path: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(upstream, tmp_path, "status") == 0

    assert capsys.readouterr().out == (
        "datamining   not fetched\n"
        "teamcraft    not fetched\n"
        "universalis  not fetched\n"
        "tree         not built\n"
    )


def test_refresh_game_fetches_and_builds(
    tmp_path: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(upstream, tmp_path, "refresh", "game") == 0
    assert run(upstream, tmp_path, "refresh", "market", "--scope", "Gaia") == 0
    capsys.readouterr()

    assert run(upstream, tmp_path, "status") == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == [
        f"datamining   {upstream.datamining_commit}",
        f"teamcraft    {upstream.teamcraft_commit}",
    ]
    assert lines[2].startswith("universalis  Gaia, fetched at ")
    assert lines[3] == "tree         1 items, 0 recipes"


def test_build_without_game_data_fails_with_a_hint(
    tmp_path: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(upstream, tmp_path, "build") == 1

    assert "bonsai refresh game" in capsys.readouterr().err


def test_refresh_market_shows_its_progress(
    tmp_path: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    upstream.sheets["Item"] = [
        {"#": 5057, "Name": "Iron Ingot", "ItemSearchCategory": 48},
    ]
    upstream.sheets["CraftType"] = [{"#": 1, "Name": "Smithing"}]
    upstream.sheets["RecipeLevelTable"] = [{"#": 1, "ClassJobLevel": 1, "Stars": 0}]
    upstream.sheets["Recipe"] = [
        {"#": 43, "CraftType": 1, "ItemResult": 5057, "RecipeLevelTable": 1}
    ]
    run(upstream, tmp_path, "refresh", "game")
    capsys.readouterr()

    assert run(upstream, tmp_path, "refresh", "market") == 0

    assert "pricing items: 1/1" in capsys.readouterr().err
