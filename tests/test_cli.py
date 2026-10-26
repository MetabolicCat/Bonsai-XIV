import sqlite3
from pathlib import Path

import pytest
from upstream import Upstream

from bonsai.__main__ import main


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A working directory and config directory of the test's own."""
    home = tmp_path / "home"
    (home / "config").mkdir(parents=True)
    monkeypatch.chdir(home)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    return home


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
        "overrides    none\n"
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


def test_build_reads_the_shared_then_the_personal_overrides(
    tmp_path: Path,
    home: Path,
    upstream: Upstream,
    capsys: pytest.CaptureFixture[str],
) -> None:
    shared = home / "overrides.toml"
    shared.write_text(
        "[[source]]\nitem = 5057\nkind = 'drop'\nref = 1\n"
        "[[source]]\nitem = 5057\nkind = 'drop'\nref = 2\n"
    )
    personal = home / "config" / "bonsai-xiv" / "overrides.toml"
    personal.parent.mkdir()
    personal.write_text(
        "[[source]]\nitem = 5057\nkind = 'drop'\nref = 1\nremove = true\n"
    )

    assert run(upstream, tmp_path / "cache", "refresh", "game") == 0
    capsys.readouterr()
    assert run(upstream, tmp_path / "cache", "status") == 0

    db = sqlite3.connect(tmp_path / "cache" / "bonsai.sqlite")
    assert db.execute("SELECT item_id, kind, ref FROM source").fetchall() == [
        (5057, "drop", 2)
    ]
    assert capsys.readouterr().out.splitlines()[-1] == (
        f"overrides    overrides.toml (2 sources), {personal} (1 source)"
    )


def test_a_mistake_in_an_override_fails_with_its_file(
    tmp_path: Path, home: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    (home / "overrides.toml").write_text("[[source]]\nitem = 1\nkind = 'drop'\n")

    assert run(upstream, tmp_path / "cache", "refresh", "game") == 1

    assert "overrides.toml: unknown item 1" in capsys.readouterr().err
