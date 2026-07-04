"""Mock-SDK tests for the FLIR backend (FlirCameraBase/FlirCamera) and its
attribute-compatibility helpers."""

import numpy as np
import pytest

from openhsi.cameras import FlirCamera, get_min_exposure, set_camera_attribute

from fakes.pyspin import BFS_NODES, GS3_NODES, FakeFlirCamera

FLIR_SETTINGS = dict(resolution=[1080, 1440], win_resolution=[0, 0],
                     win_offset=[0, 0], pixel_format="Mono16", exposure_ms=10)


def make_cam(write_settings, n_lines=3, settings=None, **cam_kwargs):
    merged = {**FLIR_SETTINGS, **(settings or {})}
    json_path = write_settings(**merged)
    return FlirCamera(json_path=json_path, n_lines=n_lines,
                      warn_mem_use=False, **cam_kwargs)


# --- helper-function unit tests (no camera class involved) -------------------

def test_set_attribute_primary_name():
    cam = FakeFlirCamera(GS3_NODES, 1440, 1080)
    assert set_camera_attribute(cam, "AcquisitionFrameRateEnabled", True)
    assert cam.AcquisitionFrameRateEnabled is True


def test_set_attribute_falls_back_to_alternative():
    cam = FakeFlirCamera(BFS_NODES, 1440, 1080)   # BFS has ...Enable, not ...Enabled
    assert set_camera_attribute(cam, "AcquisitionFrameRateEnabled", True,
                                alternatives=["AcquisitionFrameRateEnable"])
    assert cam.AcquisitionFrameRateEnable is True


def test_set_attribute_missing_not_required():
    cam = FakeFlirCamera(BFS_NODES, 1440, 1080)
    assert set_camera_attribute(cam, "AcquisitionFrameRateAuto", "Off",
                                required=False) is False


def test_set_attribute_missing_required_raises_with_hint():
    cam = FakeFlirCamera(BFS_NODES, 1440, 1080)
    with pytest.raises(AttributeError, match="AcquisitionFrameRateEnable"):
        set_camera_attribute(cam, "AcquisitionFrameRateEnabled", True)


@pytest.mark.parametrize("nodes,expected", [
    (GS3_NODES, 19.0),    # ExposureMinAbsVal_Float
    (BFS_NODES, 20.0),    # ExposureMin
    ({"ExposureTime": 10.0}, 1.0),   # nothing found -> safe default
])
def test_get_min_exposure(nodes, expected):
    cam = FakeFlirCamera(nodes, 1440, 1080)
    assert get_min_exposure(cam) == pytest.approx(expected)


# --- FlirCamera construction ---------------------------------------------------

@pytest.mark.parametrize("style", ["BFS", "GS3"])
def test_connects_and_configures(style, fake_flir_factory, write_settings):
    mod = fake_flir_factory(style=style)
    cam = make_cam(write_settings)
    flir = mod.last_camera()
    assert flir.initialized
    assert flir.GainAuto == "Off" and flir.Gain == 0
    assert flir.ExposureAuto == "Off"
    assert flir.ExposureTime == pytest.approx(10_000.0)
    # frame rate derived from exposure: int(min(1000/(10+1), 120)) == 90
    assert flir.AcquisitionFrameRate == 90
    # window falls back to the full sensor when win_resolution is (0, 0)
    assert flir.Width == 1440 and flir.Height == 1080


def test_get_img_returns_frame(fake_flir, write_settings):
    cam = make_cam(write_settings)
    frame = np.arange(12, dtype=np.uint16).reshape(3, 4)
    fake_flir.last_camera().queue_frame(frame)
    np.testing.assert_array_equal(cam.get_img(), frame)


def test_set_exposure_clamps_to_device_minimum(fake_flir, write_settings):
    cam = make_cam(write_settings)
    cam.set_exposure(0.001)   # below the 20 us (0.02 ms) device minimum
    assert cam.settings["exposure_ms"] == pytest.approx(0.02)
    assert fake_flir.last_camera().ExposureTime == pytest.approx(20.0)
    assert fake_flir.last_camera().AcquisitionFrameRate == 120  # hits the cap


def test_get_temp(fake_flir, write_settings):
    cam = make_cam(write_settings)
    assert cam.get_temp() == pytest.approx(25.0)


@pytest.mark.xfail(raises=NameError, strict=True,
                   reason="known bug: cameras.py polls flircam.initialized "
                          "with sleep(0.1) but never imports sleep")
def test_slow_initialisation_polls(fake_flir_factory, write_settings):
    fake_flir_factory(init_delay=1)   # camera not initialized on first check
    make_cam(write_settings)
