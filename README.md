# Bonsai XIV

**A decision tool for what is actually worth hoarding in FFXIV.**

Bonsai maintains a dependency tree of every craftable item and prunes
it down to the recipes and materials that are genuinely worth your
time, inventory, and gil — and, by extension, tells you which base
ingredients are worth stockpiling.

The problem statement and the intended pruning rules are described in
[bonsai-xiv.md](bonsai-xiv.md).

## Status

Milestone 1, in progress: build the recipe tree from its sources,
refresh it, and cache it locally. Pruning rules and the UI to
experiment with them come in milestone 2.

## Install

Bonsai needs Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/RKI027/Bonsai-XIV.git
cd Bonsai-XIV
make install
```

## Usage

```sh
uv run bonsai refresh game      # fetch the latest game data, then build
uv run bonsai refresh market    # fetch market prices, then build
uv run bonsai build             # rebuild the tree from the cache, offline
uv run bonsai status            # show what the cache holds and how old it is
```

`refresh game` downloads the game data only when its sources have
moved since the last fetch. `refresh market` fetches prices for every
marketable item in the tree from the `Japan` region by default; use
`--region` for another Universalis region, data center or world.

Everything goes in the cache directory, `$XDG_CACHE_HOME/bonsai-xiv`
(`~/.cache/bonsai-xiv` by default), or the one given with
`--cache-dir`:

- `sources/` holds the downloaded files, verbatim, under the version
  they were fetched at;
- `bonsai.sqlite` is the tree built from them.

`build` reads only the cache, so the same cache always builds the same
tree. See [docs/sources.md](docs/sources.md) for where the data comes
from and how each source is updated, and
[docs/tree.md](docs/tree.md) for the tables in `bonsai.sqlite`.

## Development

```sh
make install    # install dependencies in .venv
./check.sh      # lock, lint, typecheck, shellcheck and tests: what CI runs
```

## License

Bonsai XIV is free software: you can redistribute it and/or modify it
under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. See [LICENSE](LICENSE).

FINAL FANTASY XIV is a registered trademark of Square Enix Holdings
Co., Ltd. Bonsai XIV is not affiliated with or endorsed by Square Enix.
