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
