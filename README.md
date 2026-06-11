# OpenHSI Design Documents

This orphan branch holds forward-looking design proposals for the `openhsi`
package. It intentionally shares no history with the code branches — design
docs are reviewed and merged here, never into the code tree.

## Status key

| Status | Meaning |
|---|---|
| Draft | Written, awaiting maintainer review |
| Accepted | Agreed direction, implementation may begin |
| In progress | Implementation underway (linked PR) |
| Done | Shipped |
| Rejected / Superseded | Kept for the record |

## Proposals

| # | Title | Status | Depends on |
|---|---|---|---|
| [0001](proposals/0001-mock-sdk-test-layer.md) | Mock-SDK test layer for camera backends | Draft | — |
| [0002](proposals/0002-packaging-modernisation.md) | Packaging modernisation and install extras | Draft | — (full scope unlocked by 0003) |
| [0003](proposals/0003-drop-nbdev-and-repo-reset.md) | Drop nbdev, make `.py` the source of truth, reset the repository | Draft | 0001 recommended first |
| [0004](proposals/0004-architecture-refactor.md) | Composition-based camera architecture, settings schema, named processing levels | Draft | 0003 (rides along with the reset) |

## Recommended sequencing

1. **0001** lands first, on the current code base, under nbdev. It is pure
   addition (a `tests/` directory + CI step), gives camera logic its first CI
   coverage, and carries over unchanged through everything that follows.
2. **0002 (part A)** — the items that don't conflict with nbdev (lazy viz
   imports, honest `python_requires`, dependency hygiene) — can land any time.
3. **0003** is the strategic decision: drop nbdev, `.py` source of truth, and
   a repository reset (new repo, filtered history, old repo archived).
   **0002 (part B)** (full `pyproject.toml`) lands as part of it.
4. **0004** is implemented in the new repository, where the refactor isn't
   fighting the notebook cell structure.

## Baseline assumptions

- Proposals are written against the state of PR
  [openhsi/openhsi#62](https://github.com/openhsi/openhsi/pull/62)
  (Hikrobot backend, nbdev 2.3.x toolchain pins, v0.4.3) and assume it has
  merged to `master`.
- Measurements quoted in 0003 were taken 2026-06-11 on a 195-commit partial
  clone of `openhsi/openhsi`; full history is larger.
