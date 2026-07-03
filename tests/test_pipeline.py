"""Processing-pipeline recipe tests: no vendor SDKs, uses the shipped example
settings/calibration from nbs/assets/."""

import copy
from pathlib import Path

import numpy as np
import pytest

from openhsi.cameras import SimulatedCamera
from openhsi.data import CameraProperties

ASSETS = Path(__file__).parent.parent / "nbs" / "assets"
JSON_PATH = str(ASSETS / "cam_settings.json")
CAL_PATH = str(ASSETS / "cam_calibration.nc")

# lvl -> expected transform-method names (from CameraProperties.set_processing_lvl)
RECIPES = {
    -1: [],
    0: ["crop"],
    1: ["crop", "fast_smile"],
    2: ["crop", "fast_smile", "fast_bin"],
    3: ["crop", "fast_smile", "slow_bin"],
    4: ["crop", "fast_smile", "fast_bin", "dn2rad"],
    5: ["crop", "fast_smile", "dn2rad", "fast_bin"],
    6: ["crop", "fast_smile", "fast_bin", "dn2rad", "rad2ref_6SV"],
    7: ["crop", "fast_smile", "dn2rad", "slow_bin"],
    8: ["crop", "fast_smile", "dn2rad", "slow_bin", "rad2ref_6SV"],
}
# calibration keys each level's tfm_setup needs beyond the basics
NEEDS = {4: {"rad_ref", "sfit"}, 5: {"rad_ref", "sfit"},
         6: {"rad_ref", "sfit", "rad_fit"}, 7: {"rad_ref", "sfit"},
         8: {"rad_ref", "sfit", "rad_fit"}}


@pytest.fixture(scope="module")
def _props_template():
    # Load the calibration NetCDF exactly once per module:
    # load_calibration_data_from_netcdf leaves the xarray dataset open, and
    # repeatedly re-opening the same file segfaults HDF5 eventually.
    return CameraProperties(json_path=JSON_PATH, cal_path=CAL_PATH)


@pytest.fixture
def props(_props_template):
    # Fresh object per test (deepcopy) because set_processing_lvl leaks state
    # between calls (see test_reconfiguring_processing_level_is_stateless).
    return copy.deepcopy(_props_template)


def _skip_if_unsupported(props, lvl):
    missing = NEEDS.get(lvl, set()) - set(props.calibration.keys())
    if missing:
        pytest.skip(f"shipped calibration lacks {sorted(missing)} for lvl {lvl}")


@pytest.mark.parametrize("lvl", sorted(RECIPES))
def test_recipe_composition(props, lvl):
    _skip_if_unsupported(props, lvl)
    props.set_processing_lvl(lvl)
    assert [t.__name__ for t in props.tfm_list] == RECIPES[lvl]


@pytest.mark.parametrize("lvl", [2, 3, 4, 5, 7])
def test_binned_and_radiance_levels_are_float32(props, lvl):
    _skip_if_unsupported(props, lvl)
    props.set_processing_lvl(lvl)
    assert props.dtype_out == np.float32


def test_lvl0_crops_to_row_slice(props):
    props.set_processing_lvl(0)
    out = props.pipeline(props.calibration["flat_field_pic"])
    assert out.shape[0] == np.ptp(props.settings["row_slice"])
    assert out.shape == props.dc_shape[:1] + props.dc_shape[1:]


def test_binning_reduces_spectral_axis(props):
    props.set_processing_lvl(1)
    unbinned = props.pipeline(props.calibration["flat_field_pic"]).shape
    props.set_processing_lvl(2)
    binned = props.pipeline(props.calibration["flat_field_pic"]).shape
    assert binned[1] < unbinned[1]


@pytest.mark.parametrize("pixel_format,expected", [
    ("Mono8", np.uint8), ("Mono10", np.uint16), ("Mono12", np.uint16),
    ("Mono16", np.uint16), ("XI_RAW16", np.uint16), ("Mono12Packed", np.uint16),
])
def test_dtype_in_from_pixel_format(write_settings, pixel_format, expected):
    props = CameraProperties(json_path=write_settings(pixel_format=pixel_format))
    props.set_processing_lvl(-1)
    assert props.dtype_in == expected


def test_custom_tfms_override_presets(props):
    marker = lambda x: x
    props.set_processing_lvl(2, custom_tfms=[marker])
    assert props.tfm_list == [marker]


@pytest.mark.xfail(raises=ValueError, strict=True,
                   reason="known bug: set_processing_lvl(4) sets "
                          "need_rad_after_fast_bin and never clears it, so a "
                          "later set_processing_lvl(5) on the same object bins "
                          "the dn2rad reference data twice and the pipeline "
                          "raises a broadcast ValueError (proposal 0004)")
def test_reconfiguring_processing_level_is_stateless(props):
    _skip_if_unsupported(props, 5)
    props.set_processing_lvl(4)
    props.set_processing_lvl(5)
    out = props.pipeline(props.calibration["flat_field_pic"])
    assert out.shape == props.dc_shape


def test_simulated_camera_end_to_end(tmp_path):
    """Integration smoke test: the hardware-free camera collects a full cube."""
    with SimulatedCamera(img_path=str(ASSETS / "rocky_beach.png"), n_lines=8,
                         processing_lvl=2, warn_mem_use=False,
                         json_path=JSON_PATH, cal_path=CAL_PATH) as cam:
        cam.collect()
        assert cam.dc.data.shape[1] == 8
        assert cam.dc.data.dtype == np.float32
