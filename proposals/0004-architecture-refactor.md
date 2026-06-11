# 0004 — Composition-based camera architecture, settings schema, named processing levels

- **Status:** Draft
- **Author:** prepared with Claude Code, 2026-06-11
- **Depends on:** 0003 (implemented in the new repo, where classes live whole in `.py` files)

## Problems with the current design

Current shape (per `nbs/architecture_overview.ipynb`):

```
CameraProperties → DataCube → OpenHSI → {Ximea,Flir,Lucid,Hikrobot,Simulated}Camera
                 → SharedDataCube → SharedOpenHSI → Shared{…}Camera
```

1. **Every backend ships twice.** The `Shared*` twin tree exists only to swap
   the storage layer; adding Hikrobot meant adding two classes; 5 backends ×
   2 = 10 leaf classes for one degree of freedom.
2. **kwargs plumbing is implicit and inconsistent.** `CameraProperties`
   overrides only keys already present in settings; `OpenHSI.__init__` then
   does `settings.update(kwargs)` wholesale. Result: real bugs —
   `XimeaCamera(exposure_ms=5)` is silently ignored because the base-class
   signature captures the kwarg before it reaches the override (encoded as
   `xfail` in proposal 0001; deliberately avoided in the Hikrobot backend).
3. **Cross-backend conventions drift.** `binxy[0]` is *vertical* binning for
   Ximea but *horizontal* for Lucid. `win_offset` fallback semantics differ.
   Nothing enforces the hardware interface (`start_cam`/`get_img`/…) — it's a
   naming convention, not a contract.
4. **`@patch` scatters classes** across notebook cells (a constraint that
   disappears with 0003, leaving `@patch` as pure indirection).
5. **Settings are unvalidated JSON.** A typo'd key or wrong-order pair fails
   deep inside a vendor SDK call with an opaque error — the field-user
   failure mode.
6. **Processing levels are magic ints.** Levels 2 vs 3 differ by fast/slow
   binning; 4 vs 5 by bin/radiance order; discoverable only by reading
   `set_processing_lvl`.

## Target architecture

Three small objects, composed:

```python
class CameraHardware(Protocol):
    """The complete hardware contract (today: an informal naming convention)."""
    def open(self) -> None: ...
    def close(self) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def get_frame(self) -> np.ndarray: ...
    def set_exposure_ms(self, value: float) -> float: ...   # returns actual
    def get_temperature(self) -> float: ...                  # NaN if unsupported
    @property
    def shape(self) -> tuple[int, int]: ...

@dataclass
class CameraSettings:              # pydantic model in practice
    settings_version: int = 2
    exposure_ms: float
    pixel_format: str
    binning: tuple[int, int]       # explicit (horizontal, vertical) — drift fixed
    window: Window | None          # height/width/offset_y/offset_x, validated
    row_slice: tuple[int, int]
    luminance: float
    ...
    @classmethod
    def load(cls, path) -> "CameraSettings":
        """Accepts v1 JSON (current files) and migrates with warnings."""

class Camera:                      # ONE capture engine, no Shared* twin
    def __init__(self, hardware: CameraHardware, settings: CameraSettings,
                 calibration: Calibration, pipeline: Pipeline | ProcessingLevel,
                 n_lines: int, buffer: Literal["local", "shared"] = "local"):
        ...
    def collect(self) -> DataCube: ...
```

- **Backends become adapters** (`XimeaHardware`, `HikrobotHardware`, …):
  ~the current `*CameraBase` bodies, minus inheritance gymnastics, with the
  SDK kept lazy. Adding a vendor = one class implementing the Protocol +
  mock-SDK tests (0001 fakes plug straight into this contract).
- **Shared memory is a constructor option** (`buffer="shared"`), not a class
  tree. The `SharedCircArrayBuffer`/multiprocessing-save machinery moves
  behind the storage choice. 10 leaf classes → 5 adapters + 1 engine.
- **Settings flow has one rule:** constructor kwargs > settings file >
  defaults, applied in `CameraSettings`, with unknown keys raising. The
  Ximea exposure bug class becomes structurally impossible.

### Processing pipeline

```python
class ProcessingLevel(IntEnum):     # ints preserved for back-compat
    RAW = -1
    CROPPED = 0
    SMILE_CORRECTED = 1
    BINNED_FAST = 2
    BINNED_SLOW = 3
    RADIANCE_FAST_BIN = 4
    RADIANCE_THEN_BIN = 5
    REFLECTANCE_FAST = 6
    RADIANCE_SLOW_BIN = 7
    REFLECTANCE_SLOW = 8

Pipeline = list[Transform]          # a level is just a named preset Pipeline
```

`Camera(..., pipeline=3)` keeps working; `ProcessingLevel.BINNED_SLOW` is the
documented spelling; custom chains pass a list, as `custom_tfms` does today.
The transforms themselves (`crop`, `fast_smile`, `dn2rad`, …) move from
`@patch`-ed methods to free functions over `(frame, calibration)` — unit
testable in isolation (`test_pipeline.py` in 0001 seeds this).

## Backwards compatibility

v1.x keeps shims so existing scripts and tutorials run unchanged:

```python
# openhsi/cameras.py (shim layer, emits DeprecationWarning)
class LucidCamera(_CompatCamera):    # wraps Camera(LucidHardware(...), ...)
    ...
class SharedLucidCamera(_CompatCamera):   # buffer="shared"
    ...
```

Context-manager usage, `collect()`, `show()`, `save()` signatures preserved.
Shims removed in 2.0. Settings v1 JSON loads forever (cheap migration code).

## Migration order (each step shippable)

1. `CameraSettings` model + loader, used *internally* by `CameraProperties`
   (validation arrives without API change; `binxy` semantics documented and
   normalised per backend).
2. `ProcessingLevel` enum + transforms as free functions; `set_processing_lvl`
   delegates.
3. `CameraHardware` protocol + adapters extracted from `*CameraBase`; leaf
   classes become shims; 0001 fakes re-pointed at adapters (tests stay green
   throughout — that's the regression harness).
4. `buffer="shared"` storage option; `Shared*` classes become shims; the
   `shared.py` class tree collapses.
5. `@patch` elimination and type annotations; mypy in CI (gradual, per-module).

## Acceptance criteria

- One new backend = one adapter class + one fake + tests; no twin classes.
- `XimeaCamera(exposure_ms=5)` honours the kwarg (the 0001 `xfail` flips).
- Malformed settings JSON fails at load with a named-field error, not inside
  an SDK call.
- All v0.4 tutorial notebooks pass unmodified against the v1.x shims.

## Effort

The largest item (2–4 weeks elapsed, incremental PRs). Steps 1–2 are
low-risk and immediately useful; steps 3–4 are the payoff; step 5 is
housekeeping that can trail.
