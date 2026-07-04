"""How constructor kwargs flow into `settings` — the documented contract and
the known deviations.

Two different override semantics exist in the class chain today:
- CameraProperties only overrides keys already present in the settings file;
- OpenHSI.__init__ then does settings.update(kwargs) wholesale.
These tests pin down the current behaviour so refactors (design proposal
0004) change it deliberately, not accidentally.
"""

import pytest

from openhsi.cameras import HikrobotCamera, XimeaCamera
from openhsi.data import CameraProperties


def test_kwarg_overrides_existing_settings_key(write_settings):
    props = CameraProperties(json_path=write_settings(exposure_ms=10),
                             exposure_ms=5)
    assert props.settings["exposure_ms"] == 5


def test_unknown_kwarg_is_not_added_to_settings(write_settings):
    props = CameraProperties(json_path=write_settings(), not_a_real_key=1)
    assert "not_a_real_key" not in props.settings


def test_openhsi_stores_all_kwargs_in_settings(fake_mvs, write_settings):
    """OpenHSI.__init__ copies every remaining kwarg into settings wholesale
    (documented current behaviour, not necessarily desirable)."""
    cam = HikrobotCamera(json_path=write_settings(), n_lines=4,
                         warn_mem_use=False)
    assert cam.settings["n_lines"] == 4


def test_hikrobot_exposure_kwarg_reaches_hardware(fake_mvs, write_settings):
    """Hikrobot deliberately does NOT capture exposure_ms in its signature, so
    the kwarg flows through to the settings override and the device."""
    cam = HikrobotCamera(json_path=write_settings(exposure_ms=10),
                         exposure_ms=5, n_lines=4, warn_mem_use=False)
    assert cam.settings["exposure_ms"] == pytest.approx(5.0)
    assert fake_mvs.last_camera().floats["ExposureTime"] == pytest.approx(5000.0)


@pytest.mark.xfail(strict=True,
                   reason="known bug: XimeaCameraBase.__init__ captures "
                          "exposure_ms in its signature, so the kwarg never "
                          "reaches the CameraProperties settings override and "
                          "is silently ignored (design proposal 0004)")
def test_ximea_exposure_kwarg_reaches_hardware(fake_xiapi, write_settings):
    cam = XimeaCamera(json_path=write_settings(exposure_ms=10,
                                               resolution=[644, 800],
                                               pixel_format="XI_RAW16"),
                      exposure_ms=5, n_lines=4, warn_mem_use=False)
    assert cam.settings["exposure_ms"] == pytest.approx(5.0)
