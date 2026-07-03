"""Mock-SDK tests for the Hikrobot backend (HikrobotCameraBase/HikrobotCamera)."""

import math

import numpy as np
import pytest

from openhsi.cameras import HikrobotCamera


def make_cam(write_settings, n_lines=4, **cam_kwargs):
    json_path = write_settings(**cam_kwargs.pop("settings", {}))
    return HikrobotCamera(json_path=json_path, n_lines=n_lines,
                          warn_mem_use=False, **cam_kwargs)


def test_connects_and_configures(fake_mvs, write_settings):
    cam = make_cam(write_settings)
    hik = fake_mvs.last_camera()
    assert hik.opened
    assert fake_mvs.initialize_calls == 1
    # free-run with manual exposure/gain, to match calibration data
    assert hik.enums_by_value["TriggerMode"] == fake_mvs.MV_TRIGGER_MODE_OFF
    assert hik.enums_by_string["ExposureAuto"] == "Off"
    assert hik.enums_by_string["GainAuto"] == "Off"
    assert hik.floats["Gain"] == 0.0
    assert hik.enums_by_string["PixelFormat"] == "Mono10"
    # full-frame window when win_resolution is (0, 0)
    assert (cam.rows, cam.cols) == (1024, 1280)
    assert hik.ints["Width"]["cur"] == 1280 and hik.ints["Height"]["cur"] == 1024


def test_custom_window(fake_mvs, write_settings):
    cam = make_cam(write_settings,
                   settings=dict(win_resolution=[512, 640], win_offset=[8, 4]))
    hik = fake_mvs.last_camera()
    assert (cam.rows, cam.cols) == (512, 640)
    assert hik.ints["Height"]["cur"] == 512 and hik.ints["Width"]["cur"] == 640
    assert hik.ints["OffsetY"]["cur"] == 8 and hik.ints["OffsetX"]["cur"] == 4


def test_serial_selection(fake_mvs_factory, write_settings):
    mod = fake_mvs_factory(serials=("AAA111", "BBB222"))
    make_cam(write_settings, serial_num="BBB222")
    # the chosen device's serial is what the backend read back
    hik = mod.last_camera()
    raw = bytes(hik.device_info.SpecialInfo.stUsb3VInfo.chSerialNumber)
    assert raw.split(b"\x00")[0].decode() == "BBB222"


def test_serial_no_match_raises(fake_mvs, write_settings):
    with pytest.raises(RuntimeError, match="serial number"):
        make_cam(write_settings, serial_num="NOPE")


def test_no_devices_raises(fake_mvs_factory, write_settings):
    fake_mvs_factory(serials=())
    with pytest.raises(RuntimeError, match="No Hikrobot camera found"):
        make_cam(write_settings)


def test_unsupported_pixel_format_raises(fake_mvs, write_settings):
    with pytest.raises(RuntimeError, match="PixelFormat"):
        make_cam(write_settings, settings=dict(pixel_format="Mono12Packed"))


def test_get_img_mono8(fake_mvs, write_settings):
    cam = make_cam(write_settings, settings=dict(pixel_format="Mono8"))
    hik = fake_mvs.last_camera()
    frame = np.arange(1024 * 1280, dtype=np.uint8).reshape(1024, 1280)
    hik.queue_frame(frame)
    img = cam.get_img()
    assert img.dtype == np.uint8 and img.shape == (1024, 1280)
    np.testing.assert_array_equal(img, frame)


def test_get_img_mono12_roundtrip(fake_mvs, write_settings):
    cam = make_cam(write_settings, settings=dict(pixel_format="Mono12"))
    hik = fake_mvs.last_camera()
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 4096, size=(1024, 1280), dtype=np.uint16)
    hik.queue_frame(frame)
    img = cam.get_img()
    assert img.dtype == np.uint16
    np.testing.assert_array_equal(img, frame)


def test_get_img_rejects_packed_length(fake_mvs, write_settings):
    """A frame whose byte count is neither H*W nor 2*H*W (e.g. packed 12-bit)
    must raise, not return a garbled cube."""
    cam = make_cam(write_settings)
    hik = fake_mvs.last_camera()
    w, h = 1280, 1024
    hik.queue_raw(bytes(w * h * 3 // 2), w, h)
    with pytest.raises(RuntimeError, match="unpacked pixel format"):
        cam.get_img()


def test_set_exposure_stores_actual(fake_mvs, write_settings):
    cam = make_cam(write_settings)
    cam.set_exposure(7.4999)   # fake rounds ExposureTime to whole microseconds
    assert cam.settings["exposure_ms"] == pytest.approx(7.5, abs=1e-3)
    assert fake_mvs.last_camera().floats["ExposureTime"] == pytest.approx(7500.0)


def test_get_temp(fake_mvs, write_settings):
    cam = make_cam(write_settings)
    assert cam.get_temp() == pytest.approx(42.5)


def test_get_temp_missing_node_is_nan(fake_mvs_factory, write_settings):
    fake_mvs_factory(has_temperature_node=False)
    cam = make_cam(write_settings)
    assert math.isnan(cam.get_temp())


def test_collect_fills_datacube(fake_mvs, write_settings):
    n_lines = 4
    with make_cam(write_settings, n_lines=n_lines) as cam:
        cam.collect()
        assert cam.dc.data.shape == (1024, n_lines, 1280)
        assert cam.cam_temperatures.data[0] == pytest.approx(42.5)
    hik = fake_mvs.last_camera()
    # trigger mode was configured before acquisition started
    names = [c[0] for c in hik.calls]
    assert names.index("MV_CC_SetEnumValue") < names.index("MV_CC_StartGrabbing")
    # context-manager exit released the camera
    assert names[-2:] == ["MV_CC_CloseDevice", "MV_CC_DestroyHandle"]
    assert not hik.grabbing and not hik.opened
