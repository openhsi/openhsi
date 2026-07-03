"""Mock-SDK tests for the Ximea backend (XimeaCameraBase/XimeaCamera)."""

import numpy as np
import pytest

from openhsi.cameras import XimeaCamera

XIMEA_SETTINGS = dict(resolution=[644, 800], win_resolution=[0, 0],
                      win_offset=[0, 0], pixel_format="XI_RAW16", exposure_ms=2)


def make_cam(fake, write_settings, n_lines=4, settings=None, **cam_kwargs):
    merged = {**XIMEA_SETTINGS, **(settings or {})}
    json_path = write_settings(**merged)
    return XimeaCamera(json_path=json_path, n_lines=n_lines,
                       warn_mem_use=False, **cam_kwargs)


def test_connects_and_configures(fake_xiapi, write_settings):
    cam = make_cam(fake_xiapi, write_settings)
    xicam = fake_xiapi.last_camera()
    assert xicam.opened_by == "first"       # open_device() when no serial given
    called = [c[0] for c in xicam.calls]
    assert "enable_horizontal_flip" in called
    assert "disable_aeag" in called
    # XI_RAW16 implies 12-bit output depth with bit packing
    assert ("set_output_bit_depth", "XI_BPP_12") in xicam.calls
    assert ("enable_output_bit_packing",) in xicam.calls
    # full-frame window
    assert (cam.rows, cam.cols) == (644, 800)


def test_open_by_serial(fake_xiapi, write_settings):
    make_cam(fake_xiapi, write_settings, serial_num="XIMEA0001")
    assert fake_xiapi.last_camera().opened_by == "XIMEA0001"


def test_get_img_returns_frame(fake_xiapi, write_settings):
    cam = make_cam(fake_xiapi, write_settings)
    frame = np.arange(644 * 800, dtype=np.uint16).reshape(644, 800)
    fake_xiapi.last_camera().queue_frame(frame)
    np.testing.assert_array_equal(cam.get_img(), frame)


def test_set_exposure_stores_rounded_actual(fake_xiapi, write_settings):
    cam = make_cam(fake_xiapi, write_settings)
    cam.set_exposure(1.234)   # fake rounds to 10 us -> 1230 us
    assert cam.settings["exposure_ms"] == pytest.approx(1.23)


def test_collect_fills_datacube(fake_xiapi, write_settings):
    n_lines = 3
    with make_cam(fake_xiapi, write_settings, n_lines=n_lines) as cam:
        cam.collect()
        assert cam.dc.data.shape == (644, n_lines, 800)
    xicam = fake_xiapi.last_camera()
    assert not xicam.acquiring
