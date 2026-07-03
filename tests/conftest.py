"""Shared fixtures: fake vendor SDK modules injected via sys.modules, and a
settings-file factory.

Every camera backend imports its vendor SDK lazily inside __init__, so a fake
module registered in sys.modules before construction is indistinguishable
from the real SDK. No openhsi code changes are needed.
"""

import json
import sys

import pytest

from fakes import arena as arena_fake
from fakes import mvs as mvs_fake
from fakes import pyspin as pyspin_fake
from fakes import xiapi as xiapi_fake


@pytest.fixture
def fake_mvs(monkeypatch):
    """Default single-USB-device Hikrobot MVS SDK fake."""
    mod = mvs_fake.build_fake_mvs()
    monkeypatch.setitem(sys.modules, "MvCameraControl_class", mod)
    return mod


@pytest.fixture
def fake_mvs_factory(monkeypatch):
    """Build a customised MVS fake (device count, serials, formats, ...)."""
    def _build(**kwargs):
        mod = mvs_fake.build_fake_mvs(**kwargs)
        monkeypatch.setitem(sys.modules, "MvCameraControl_class", mod)
        return mod
    return _build


@pytest.fixture
def fake_xiapi(monkeypatch):
    ximea_pkg, xiapi_mod = xiapi_fake.build_fake_ximea()
    monkeypatch.setitem(sys.modules, "ximea", ximea_pkg)
    monkeypatch.setitem(sys.modules, "ximea.xiapi", xiapi_mod)
    return xiapi_mod


@pytest.fixture
def fake_arena(monkeypatch):
    arena_pkg, system_mod = arena_fake.build_fake_arena()
    monkeypatch.setitem(sys.modules, "arena_api", arena_pkg)
    monkeypatch.setitem(sys.modules, "arena_api.system", system_mod)
    return arena_pkg


@pytest.fixture
def fake_arena_factory(monkeypatch):
    def _build(**kwargs):
        arena_pkg, system_mod = arena_fake.build_fake_arena(**kwargs)
        monkeypatch.setitem(sys.modules, "arena_api", arena_pkg)
        monkeypatch.setitem(sys.modules, "arena_api.system", system_mod)
        return arena_pkg
    return _build


@pytest.fixture
def fake_flir(monkeypatch):
    mod = pyspin_fake.build_fake_flir()
    monkeypatch.setitem(sys.modules, "simple_pyspin", mod)
    return mod


@pytest.fixture
def fake_flir_factory(monkeypatch):
    def _build(**kwargs):
        mod = pyspin_fake.build_fake_flir(**kwargs)
        monkeypatch.setitem(sys.modules, "simple_pyspin", mod)
        return mod
    return _build


@pytest.fixture
def write_settings(tmp_path):
    """Write a camera settings JSON to a temp file; returns its path.

    Defaults match the shape of the shipped cam_settings_*.json assets and
    can be overridden per test (`write_settings(pixel_format="Mono8")`).
    """
    counter = {"n": 0}

    def _write(**overrides):
        base = dict(
            camera_id="0",
            row_slice=[0, -1],
            resolution=[1024, 1280],
            fwhm_nm=4,
            exposure_ms=10,
            luminance=30000,
            binxy=[1, 1],
            win_offset=[0, 0],
            win_resolution=[0, 0],
            pixel_format="Mono10",
        )
        base.update(overrides)
        counter["n"] += 1
        path = tmp_path / f"settings_{counter['n']}.json"
        path.write_text(json.dumps(base))
        return str(path)

    return _write
