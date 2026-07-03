"""Mock-SDK tests for the Lucid Vision backend (LucidCameraBase/LucidCamera)."""

import numpy as np
import pytest

from openhsi.cameras import LucidCamera

LUCID_SETTINGS = dict(resolution=[1080, 1440], win_resolution=[0, 0],
                      win_offset=[0, 0], pixel_format="Mono12Packed",
                      exposure_ms=10)


def make_cam(write_settings, n_lines=3, settings=None, **cam_kwargs):
    merged = {**LUCID_SETTINGS, **(settings or {})}
    json_path = write_settings(**merged)
    return LucidCamera(json_path=json_path, n_lines=n_lines,
                       warn_mem_use=False, **cam_kwargs)


def test_connects_and_configures(fake_arena, write_settings):
    cam = make_cam(write_settings)
    dev = fake_arena.last_device()
    # stream tuning applied
    assert dev.tl_stream_nodemap["StreamAutoNegotiatePacketSize"].value is True
    assert dev.tl_stream_nodemap["StreamPacketResendEnable"].value is True
    # manual exposure/gain to match calibration data
    assert dev.nodemap["ExposureAuto"].value == "Off"
    assert dev.nodemap["Gain"].value == 0.0
    assert dev.nodemap["PixelFormat"].value == "Mono12Packed"
    # full-frame window
    assert (cam.rows, cam.cols) == (1080, 1440)
    assert cam.settings["camera_id"] == "FakeLucid"


def test_get_img_unpacks_mono12(fake_arena, write_settings):
    """Craft a packed 12-bit buffer with known pixel values and check the
    unpacking branch reconstructs them exactly."""
    cam = make_cam(write_settings)
    dev = fake_arena.last_device()
    frame = np.array([[0x001, 0xFFF, 0xABC, 0x123],
                      [0x800, 0x0F0, 0x555, 0xAAA]], dtype=np.uint16)
    dev.queue_frame(frame)
    img = cam.get_img()
    assert img.shape == frame.shape
    np.testing.assert_array_equal(img, frame)


def test_get_img_mono8(fake_arena, write_settings):
    cam = make_cam(write_settings, settings=dict(pixel_format="Mono8"))
    dev = fake_arena.last_device()
    frame = np.arange(16, dtype=np.uint8).reshape(4, 4)
    dev.queue_frame(frame)
    np.testing.assert_array_equal(cam.get_img(), frame)


def test_get_img_mono16(fake_arena, write_settings):
    cam = make_cam(write_settings, settings=dict(pixel_format="Mono16"))
    dev = fake_arena.last_device()
    frame = (np.arange(16, dtype=np.uint16) * 1000).reshape(4, 4)
    dev.queue_frame(frame)
    np.testing.assert_array_equal(cam.get_img(), frame)


def test_set_exposure_enables_framerate_cap(fake_arena, write_settings):
    cam = make_cam(write_settings)
    dev = fake_arena.last_device()
    # long exposure: nominal framerate 0.98e6/us below max -> cap engaged
    cam.set_exposure(50)
    assert dev.nodemap["AcquisitionFrameRateEnable"].value is True
    assert dev.nodemap["AcquisitionFrameRate"].value == pytest.approx(19.6)
    assert cam.settings["exposure_ms"] == pytest.approx(50)
    # short exposure: nominal framerate above device max -> cap disabled
    cam.set_exposure(5)
    assert dev.nodemap["AcquisitionFrameRateEnable"].value is False
    assert dev.nodemap["ExposureTime"].value == pytest.approx(5000.0)


def test_set_exposure_clamps_to_minimum(fake_arena, write_settings):
    cam = make_cam(write_settings)
    cam.set_exposure(0.001)   # below the 20 us device minimum
    assert cam.settings["exposure_ms"] == pytest.approx(0.02)


@pytest.mark.xfail(raises=NameError, strict=True,
                   reason="known bug: cameras.py catches DeviceNotFoundError "
                          "without importing it, so the handler itself raises "
                          "NameError instead of the intended RuntimeError")
def test_no_device_raises_friendly_error(fake_arena_factory, write_settings):
    fake_arena_factory(n_devices=0)
    with pytest.raises(RuntimeError, match="connect a lucid vision camera"):
        make_cam(write_settings)


@pytest.mark.xfail(raises=NameError, strict=True,
                   reason="known bug: get_mac references undefined global "
                          "'cam' instead of self")
def test_get_mac(fake_arena, write_settings):
    cam = make_cam(write_settings)
    assert cam.get_mac() == "1c:0f:af:01:7b:a0"
