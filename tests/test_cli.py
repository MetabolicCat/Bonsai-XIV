import sqlite3
from pathlib import Path

import pytest
from upstream import Upstream
from world import World

from bonsai.__main__ import main
from bonsai.cache import Cache


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


@pytest.fixture
def world(tmp_path: Path, upstream: Upstream) -> World:
    world = World(upstream, Cache(tmp_path / "cache"))
    ore, shard = world.item(1, "Iron Ore"), world.crystal(2)
    world.gathered(ore)
    ingot = world.item(10, "Iron Ingot")
    world.recipe(100, ingot, {ore: 3, shard: 1})
    sword = world.item(20, "Iron Sword")
    world.recipe(200, sword, {ingot: 2}, job="Smithing", level=20)
    world.market(sword, 1000, 1000.0, 5.0)
    world.recipe(300, world.item(30, "Iron Lance"), {ingot: 3})
    world.tree()
    return world


RULES = '[[rule]]\nname = "Gil-maker"\nwhere = "turnover > 0"\n'


def test_prune_summarises_what_the_rules_keep(
    tmp_path: Path,
    home: Path,
    world: World,
    upstream: Upstream,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (home / "rules.toml").write_text(RULES)

    assert run(upstream, tmp_path / "cache", "prune") == 0

    assert capsys.readouterr().out == (
        "Gil-maker  1 selected\n"
        "kept 2 recipes of 3, pruned 1; 2 base ingredients to hoard\n"
    )


def test_prune_shows_the_hoard_and_the_kept_recipes(
    tmp_path: Path,
    home: Path,
    world: World,
    upstream: Upstream,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rules = tmp_path / "mine.toml"
    rules.write_text(RULES)
    cache = tmp_path / "cache"

    assert run(upstream, cache, "prune", "--rules", str(rules), "--show", "hoard") == 0
    hoard = capsys.readouterr().out.splitlines()[2:]
    assert run(upstream, cache, "prune", "--rules", str(rules), "--show", "kept") == 0
    kept = capsys.readouterr().out.splitlines()[2:]

    assert hoard == [
        "Iron Ore  needed by 1  gathering",
        "Item 2    needed by 1  no known source",
    ]
    assert kept == [
        "Iron Sword  Smithing 20  Gil-maker #1",
        "Iron Ingot  Smithing 1   for Iron Sword",
    ]


def test_prune_without_rules_fails_with_a_hint(
    tmp_path: Path, home: Path, upstream: Upstream, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(upstream, tmp_path / "cache", "prune") == 1

    assert "rules.toml" in capsys.readouterr().err
