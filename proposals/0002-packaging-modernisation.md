# 0002 — Packaging modernisation and install extras

- **Status:** Draft
- **Author:** prepared with Claude Code, 2026-06-11
- **Split:** Part A lands under nbdev; Part B lands with proposal 0003

## Problem

1. **Headless capture devices pay for the full viz stack.** `openhsi.data`
   imports holoviews, panel, and bokeh at module import time; `openhsi.atmos`
   imports Py6S. A Raspberry Pi that only needs `collect()` + save currently
   installs and imports ~200 MB of visualisation/atmosphere dependencies.
2. **Metadata is fiction.** `min_python = 3.7` and classifiers for 3.6–3.10,
   while today's resolved dependencies (numpy 2.4, pandas 3.0) require ≥3.10.
   `cv2` is used by `WebCamera` but declared nowhere.
3. **Legacy packaging.** `settings.ini` + template `setup.py` (already patched
   once in PR #62 to remove `pkg_resources`). No wheels metadata via
   `pyproject.toml`, no extras mechanism.
4. **No upper-bound strategy.** Tests currently pass against numpy 2.4 /
   pandas 3.0 by luck, not policy; the pickle-calibration error message in
   `data.py` referencing "xarray not being 2022.3.0" is a fossil of a previous
   silent breakage.

## Part A — can land now, under nbdev 2.3.x

### A1. Lazy viz imports

Move holoviews/panel/bokeh imports inside the functions/classes that use them
(`DataCube.show`, the dashboard widgets), exactly as vendor SDKs already are
in `cameras.py`. Import time for `openhsi.capture` on a Pi drops dramatically;
no API change. The `hv.extension('bokeh')` calls move into the show/widget
paths.

*Compatibility note:* anything that relied on `import openhsi.data` to
initialise the holoviews extension must call `.show()`/widget APIs first —
docs notebooks already do.

### A2. Honest Python floor

`min_python = 3.10`, classifiers updated. This is not a behaviour change —
installs on ≤3.9 already fail at dependency resolution — it just makes the
failure legible.

### A3. Declare optional SDK/webcam deps in docs

`WebCamera` gets the same lazy-import + actionable-error treatment as the
vendor SDKs (`pip install opencv-python-headless` hint). Vendor SDKs stay
undeclared (not pip-installable) but get a documented matrix in the README.

## Part B — with the 0003 reset (`pyproject.toml` as the single config)

```toml
[project]
name = "openhsi"
requires-python = ">=3.10"
dependencies = [          # capture core only
  "numpy", "scipy", "xarray", "netcdf4", "h5py",
  "pandas", "tqdm", "fastprogress", "fastcore", "psutil", "pillow",
]

[project.optional-dependencies]
viz   = ["matplotlib", "holoviews", "bokeh", "panel", "param", "hvplot",
         "pyviz_comms", "streamz"]
atmos = ["Py6S"]
sensors = ["pyserial"]
all   = ["openhsi[viz,atmos,sensors]"]
dev   = ["pytest", "ruff", "mypy", "openhsi[all]"]
```

- `pip install openhsi` → capture + save on an embedded device.
- `pip install openhsi[viz]` → notebooks/dashboards.
- `pip install openhsi[atmos]` → 6SV workflows (the 6S binary itself remains a
  documented external install).
- Missing-extra imports raise a one-line actionable error
  (`"DataCube.show requires the 'viz' extra: pip install openhsi[viz]"`).

### Upper bounds policy

No blanket upper caps (they rot — see the nbdev pinning saga), but:
- a **weekly scheduled CI run against latest deps** so breakage is detected
  within days instead of at user install time;
- caps added **reactively and temporarily** with a linked issue when a real
  incompatibility ships.

### conda-forge

Feedstock split mirrors the extras (`openhsi` + `openhsi-viz` outputs, or a
single package with `run_constrained` — decide with feedstock maintainers).
Minimum change: update `dev_url`/source after 0003.

## Acceptance criteria

- `python -c "import openhsi.capture"` succeeds in a venv with only core deps,
  in < 2 s on a Pi-class machine.
- `pip install openhsi` on Python 3.9 fails with a clear "requires ≥3.10".
- Extras matrix documented in README; CI tests core-only and `[all]` installs.

## Effort

Part A: ~1 day (mostly moving imports + smoke tests). Part B: folded into the
0003 migration PR.
