# 0003 — Drop nbdev, make `.py` the source of truth, reset the repository

- **Status:** Draft
- **Author:** prepared with Claude Code, 2026-06-11
- **Decision owners:** openhsi maintainers

## Why now

Two independent pressures point at the same moment:

### 1. The toolchain is on life support

The repo only builds/tests with a frozen 2022-era stack: `nbdev>=2.3,<2.4` +
`execnb<0.2` + `setuptools<81` (PR #62 pinned all three after CI broke).
Each pin is a countdown:

| Pin | Why it exists | What kills it |
|---|---|---|
| `nbdev<2.4` | 2.2.x silently drops `#| export cameras` cells; 2.4.x rewrites every cell marker; 3.x refuses `settings.ini` | unmaintained; any incompatible future dep |
| `execnb<0.2` | nbdev 2.x imports `execnb.nbio`, removed in 0.2 | already happened (this is the pin) |
| `setuptools<81` | nbdev 2.3.x imports `pkg_resources` at module load | `pkg_resources` is scheduled for removal ecosystem-wide; a future pip/venv will refuse |

The alternative escape — migrating to nbdev 3 + `pyproject.toml` — keeps the
project coupled to a toolchain that has now broken it three different ways,
and that most scientific contributors don't know.

### 2. The history is ~99.9 % generated artifacts (measured)

Measured 2026-06-11 on a **195-commit partial clone** (full history is
larger; CONTRIBUTING already tells users to shallow-clone because of this):

| Content (across history) | Uncompressed | Share |
|---|---|---|
| `*.ipynb` revisions (outputs embedded) | 3 355 MiB (338 blobs) | ~58 % |
| `docs/` (nbdev1-era committed site builds) | 2 026 MiB (305 blobs) | ~35 % |
| `assets/` incl. two 50 MB `.nc` datacubes | ~290 MiB | ~5 % |
| **`openhsi/` — the actual library** | **3.9 MiB (256 blobs)** | **< 0.1 %** |

Pack size of this partial clone: **368 MiB**. Single notebook revisions reach
40–51 MB (`03_atmos.ipynb`, `10_tutorial_calibrate.ipynb`). The library's
entire code history would fit in a repo of ~5–15 MiB.

A fresh-start moment that fixes the history problem *and* the toolchain
problem at once is cheaper than fixing them separately.

## Proposal in one paragraph

Create a new `openhsi/openhsi` repository seeded with **filtered history**
(code paths kept, generated artifacts and notebook outputs dropped), with
`.py` files as the source of truth, plain pytest, MkDocs documentation, and
`pyproject.toml` packaging. Rename the current repository to
`openhsi/openhsi-nbdev` and archive it read-only. Release the result as
**v1.0.0**.

## What nbdev provides today → replacement

| nbdev feature | Today | Replacement |
|---|---|---|
| Source of truth | `nbs/*.ipynb` → `nbdev_export` | `openhsi/*.py` edited directly; the export step disappears |
| Library docs | Quarto site from notebook prose, gh-pages | MkDocs Material + `mkdocstrings[python]` (docstrings become the API reference) |
| Tutorials | doc notebooks with outputs committed | `docs/tutorials/*.ipynb` kept **output-stripped** (nbstripout pre-commit), executed in CI (`nbmake`) and rendered with `mkdocs-jupyter` |
| Tests | assertion cells in notebooks, `nbdev_test`, `tst_flags` | pytest (`tests/` from proposal 0001 is the seed); `#| hardware` → `@pytest.mark.hardware`; notebook tutorials still execute in CI as integration smoke tests |
| README/CONTRIBUTING generation | from `index.ipynb` / `contributing.ipynb` | plain Markdown files |
| `settings.ini` + template `setup.py` | nbdev master config | `pyproject.toml` (proposal 0002 Part B) |
| `_modidx.py`, `#| export` directives, `show_doc` | nbdev plumbing | deleted; mkdocstrings reads real docstrings |
| `nbdev_clean` git hooks | metadata stripping for *all* notebooks | `nbstripout` only for the tutorial notebooks that remain |
| Version bump / release | `nbdev_bump_version`, `nbdev_pypi` | `hatch version` (or manual) + GitHub Actions trusted publishing to PyPI |
| Per-cell docs prose | interleaved with code | docstrings (API) + tutorial notebooks (narrative); some prose will need manual rehoming during conversion — this is the main manual labour |

**What is genuinely lost:** the literate "explanation right next to the code
cell" style, and docs URLs (`…/cameras-ximea.html` etc.) change → publish a
redirect map or accept link rot from old external links.

**What is gained:** normal IDE/lint/type tooling, reviewable diffs, no
export-sync CI step, no metadata-stripping hooks, contributors don't need
nbdev knowledge, and `@patch`-scattered classes can become whole classes in
one file (enabler for proposal 0004).

## Repository strategy

### Options considered

| | Mechanics | Pros | Cons |
|---|---|---|---|
| **A. Rewrite in place** | `git filter-repo` on existing repo | keeps stars/issues/watchers | rewrites every SHA: breaks all clones, forks, open PRs, pinned links; GitHub caches old objects unpredictably. **Rejected.** |
| **B. New repo, fresh history** | single import commit | simplest, smallest | loses `git blame`/`git log` for the code |
| **C. New repo, filtered history** ⭐ | `git filter-repo` into a fresh repo | keeps code blame (~3.9 MiB of real history), drops the gigabytes | SHAs differ from the archive (expected and fine — it's a new repo) |

**Recommendation: C.** Concretely (run on a **full** clone, not shallow):

```bash
git clone --no-local --mirror git@github.com:openhsi/openhsi.git work && cd work
git filter-repo \
  --invert-paths --path docs --path assets \
  --strip-blobs-bigger-than 1M \
  --path-glob '*.ipynb' --invert-paths   # drop notebook history entirely…
# …then add back the *current* tutorial notebooks, output-stripped, in the
# migration commit. (Exact filter set to be tuned on a dry run; keep
# nbs/assets/cam_settings*.json + cam_calibration.nc current versions only.)
```

Then a conversion series on top: remove nbdev scaffolding, add
`pyproject.toml`, `tests/`, `docs/`, CI. Tag the seam clearly:
`v0.4.x-final` (last nbdev state) and `v1.0.0` (first new-world release).

### Rename-and-archive runbook

1. Freeze: merge/close open PRs on the old repo; announce the cutover in an
   issue + README banner.
2. Rename `openhsi/openhsi` → `openhsi/openhsi-nbdev`. Archive it (read-only)
   **after** step 4.
3. Create new `openhsi/openhsi` (reusing the name means existing links —
   including the published paper's `github.com/openhsi/openhsi` — resolve to
   the new repo. Note: reusing the name intentionally breaks GitHub's
   rename-redirect to the archive; the archive must be linked prominently
   from the new README).
4. Transfer the open issues worth keeping (GitHub supports in-org transfer);
   push the filtered + converted history; set up gh-pages, branch protection.
5. Re-point the periphery — this is the checklist that's easy to forget:
   - PyPI: new release from new repo; `project.urls` updated. **PyPI trusted
     publishing is bound to repo+workflow — reconfigure it.**
   - conda-forge feedstock: `dev_url`, source URL/sha.
   - Docs: `openhsi.github.io/openhsi` rebuilds from the new repo (same URL).
   - Zenodo/DOI hooks, CI badges, the paper's "code availability" can't
     change — name reuse covers it.
6. Old repo: README banner ("Archived. Development continues at …"),
   then archive.

### Version: 1.0.0 (not 2.0.0)

The package has never declared a stable API; 0.x → 1.0.0 is the semver-honest
signal ("first stable, and yes, things moved"). 2.0.0 implies a 1.x era that
never existed. The breaking changes (import-time viz removal, packaging
extras, later 0004 API) are exactly what a 1.0 boundary is for. Public import
paths (`from openhsi.cameras import LucidCamera`) are preserved at 1.0;
deeper API changes arrive in 1.x/2.0 via proposal 0004 with deprecation
shims.

## Sequencing & freeze window

1. PR #62 merges (assumed). Proposal 0001 lands under nbdev — its tests carry
   the conversion.
2. Dry-run the filter on a mirror; record final sizes; review converted tree
   on a scratch repo.
3. **Feature freeze on old repo (target: ≤ 2 weeks).** Conversion PRs into the
   scratch repo: de-nbdev, pyproject, docs, CI.
4. Cutover per runbook. v1.0.0 to PyPI/conda-forge.

## Risks

| Risk | Mitigation |
|---|---|
| Prose stranded in notebooks during conversion | conversion checklist per notebook: docstring-worthy → docstrings, narrative → tutorial/docs page; reviewed file-by-file |
| External deep links to old docs pages break | redirect map page on the new site for the top-N pages; archive keeps old site artefacts |
| Contributor muscle memory (`nbdev_export`) | CONTRIBUTING rewrite + CI failure messages that say what to do instead |
| In-flight forks/PRs orphaned | freeze window + announcement; archive remains clonable forever |
| PyPI publish pipeline misconfigured post-move | do a `1.0.0rc1` end-to-end release rehearsal before cutover |

## Decision points for maintainers

1. Approve direction: drop nbdev + new repo (vs. nbdev 3 migration)?
2. History: filtered (option C, recommended) vs fresh (option B)?
3. Archive name: `openhsi-nbdev` (descriptive) vs `openhsi-legacy`?
4. Version: confirm 1.0.0.
5. Freeze window dates.
