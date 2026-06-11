# 0001 — Mock-SDK test layer for camera backends

- **Status:** Draft
- **Author:** prepared with Claude Code, 2026-06-11
- **Implementation branch:** to be cut from `master` after PR #62 merges

## Problem

Everything behind a `#| hardware` flag has zero CI coverage, which is most of
`cameras.py`. The vendor classes contain real logic that is testable without a
camera:

- pixel-format / frame-length handling (`get_img` byte-width branching)
- window and offset arithmetic (`win_resolution`/`win_offset` fallbacks)
- serial-number device selection and the "no device found" paths
- settings overrides flowing (or silently not flowing) through `**kwargs`
- error mapping from SDK return codes (`_check`-style helpers)

Evidence this matters: the Hikrobot backend (PR #62) shipped entirely
hardware-unvalidated; the `XimeaCamera(exposure_ms=...)` override has been
silently ignored for years (see Known Bugs below); the June-2025 FLIR fixes
("properties setting fixes from hardware testing") were exactly the class of
bug a fake SDK would have caught on a laptop.

## Proposal

Add a plain `pytest` suite with fake vendor SDK modules. This is **pure
addition** — it does not touch nbdev, the notebooks, or the generated modules,
and it survives proposal 0003 unchanged.

### Why it works without refactoring

Every backend already imports its SDK *lazily inside `__init__`*
(`from ximea import xiapi`, `importlib.import_module("MvCameraControl_class")`,
`from arena_api.system import system`). That means a fake module registered in
`sys.modules` before construction is indistinguishable from the real SDK:

```python
# tests/conftest.py
import sys, types, pytest

@pytest.fixture
def fake_mvs(monkeypatch):
    """Minimal stand-in for the Hikrobot MVS SDK python bindings."""
    from tests.fakes.mvs import build_fake_mvs   # plain-Python fake
    mod = build_fake_mvs(n_devices=1, serials=["DA1234567"],
                         width=1280, height=1024)
    monkeypatch.setitem(sys.modules, "MvCameraControl_class", mod)
    return mod
```

### Layout

```
tests/
  conftest.py            # fixtures: fake_mvs, fake_xiapi, fake_arena, fake_pyspin, fake_cv2
  fakes/
    mvs.py               # scriptable fake: records calls, returns canned frames/codes
    xiapi.py
    arena.py
    pyspin.py
  test_hikrobot.py
  test_ximea.py
  test_lucid.py
  test_flir.py
  test_settings_flow.py  # kwargs → settings override semantics, shared across backends
  test_pipeline.py       # set_processing_lvl recipes against synthetic frames (no SDK at all)
```

Each fake is a ~100-line plain-Python module exposing exactly the call surface
the backend uses (enumerate, open, get/set node values, grab frame), with
knobs for: number of devices, serials, supported pixel formats, node-set
return codes, and the frame bytes returned. Fakes *record* every call so tests
can assert ordering (e.g. `TriggerMode` set before `StartGrabbing`).

### Representative test cases

```python
def test_get_img_mono12_reshape(fake_mvs, tmp_settings):
    cam = HikrobotCamera(json_path=tmp_settings(pixel_format="Mono12"), n_lines=4,
                         warn_mem_use=False)
    fake_mvs.queue_frame(np.arange(1280*1024, dtype=np.uint16))
    img = cam.get_img()
    assert img.shape == (1024, 1280) and img.dtype == np.uint16

def test_serial_selection_no_match_raises(fake_mvs, tmp_settings):
    with pytest.raises(RuntimeError, match="serial number"):
        HikrobotCamera(serial_num="NOPE", json_path=tmp_settings(), warn_mem_use=False)

def test_packed_format_rejected(fake_mvs, tmp_settings):
    ...  # frame_len not H*W or 2*H*W → RuntimeError, not a garbled cube

@pytest.mark.xfail(reason="known bug: exposure_ms captured by base signature, "
                          "never reaches CameraProperties override (see 0004)")
def test_ximea_exposure_kwarg_overrides_settings(fake_xiapi, tmp_settings):
    cam = XimeaCamera(exposure_ms=5, json_path=tmp_settings(exposure_ms=10), ...)
    assert cam.settings["exposure_ms"] == pytest.approx(5)
```

The `xfail` pattern is deliberate: known bugs get encoded as expected failures
now and flip to hard assertions when 0004 fixes the semantics.

### CI integration

One extra step in `test.yaml` (after `nbdev_test`):

```yaml
- name: Run pytest suite (mock-SDK camera tests)
  run: |
    pip install pytest
    pytest tests/ -q
```

Hardware-dependent tests (when someone runs the suite next to a real camera)
use `@pytest.mark.hardware`, registered in `pyproject.toml` / `pytest.ini`,
deselected by default — mirroring the existing `tst_flags` convention.

## Non-goals

- Not porting the existing notebook-cell tests (they keep running under
  `nbdev_test` until 0003).
- Not validating real SDK behaviour — fakes encode our *understanding* of the
  SDKs. Hardware shakedowns are still required for new backends; the fakes
  lock in regressions once a backend works.

## Acceptance criteria

- `pytest tests/` green in CI on Linux, no vendor SDKs installed.
- Coverage over `cameras.py` device-independent logic (target: every branch in
  `get_img`, device selection, and window setup for all four SDK backends).
- At least one settings-flow test per backend, with known bugs as `xfail`.

## Effort

Roughly 2–4 focused days: fakes are mechanical (the call surfaces are small —
Hikrobot uses ~15 SDK functions, Ximea ~20), tests are short. No risk to
shipped code.
