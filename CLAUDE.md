# Bonsai XIV

What it is for: [bonsai-xiv.md](bonsai-xiv.md). Where the data comes
from: [docs/sources.md](docs/sources.md). What the built tree holds:
[docs/tree.md](docs/tree.md); hand corrections to the sources:
[docs/overrides.md](docs/overrides.md); rules, primitives and pruning:
[docs/pruning.md](docs/pruning.md). Keep the docs in step with the
code.

## Commands

- `make install`, then `./check.sh` after every change: it is what CI
  runs.
- `uv run bonsai --cache-dir <dir> refresh game|market`, `build`,
  `status`. Use a scratch cache dir to try changes on the real data.

## Design

- Fetching (`refresh`, network) is separate from building (`build`,
  offline): the build reads only the cache, so the same cache gives the
  same tree.
- One module per source under `src/bonsai/sources/`.
- The real data has surprises (unnamed items, currency indexes, gaps):
  check a change against it, not only against the tests.

## Tests

Tests never touch the network: `tests/upstream.py` fakes GitHub,
Teamcraft and Universalis. A sheet column the build reads needs a
neutral default in its `DEFAULTS`, and a test that changes sheets after
a refresh must move the fake commit.
