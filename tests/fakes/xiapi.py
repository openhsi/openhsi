"""Fake Ximea SDK (`ximea.xiapi`) mirroring the surface used by XimeaCameraBase."""

import types
from collections import deque

import numpy as np


class FakeXiImage:
    def __init__(self):
        self._array = None

    def get_image_data_numpy(self):
        return self._array


class FakeXiCamera:
    def __init__(self, module):
        self._mod = module
        self.calls = []
        self.opened_by = None
        self.acquiring = False
        self.frames = deque()
        self.height = module.height_max
        self.width = module.width_max
        self.offset_x = 0
        self.offset_y = 0
        self.exposure_us = 10000.0
        self.gain = 0.0
        self.imgdataformat = "XI_MONO8"
        self.binning_vertical = 1

    def _record(self, *call):
        self.calls.append(call)

    def queue_frame(self, array):
        self.frames.append(np.ascontiguousarray(array))

    # -- device lifecycle --------------------------------------------------
    def open_device(self):
        self._record("open_device",)
        self.opened_by = "first"

    def open_device_by_SN(self, serial):
        self._record("open_device_by_SN", serial)
        if serial != self._mod.serial:
            raise RuntimeError(f"Xi_error: no device with serial {serial}")
        self.opened_by = serial

    def close_device(self):
        self._record("close_device",)

    def get_device_sn(self):
        return self._mod.serial

    # -- configuration -------------------------------------------------------
    def enable_horizontal_flip(self):
        self._record("enable_horizontal_flip",)

    def set_binning_vertical(self, v):
        self._record("set_binning_vertical", v)
        self.binning_vertical = v

    def set_binning_vertical_mode(self, mode):
        self._record("set_binning_vertical_mode", mode)

    def set_height(self, v): self._record("set_height", v); self.height = v
    def set_width(self, v): self._record("set_width", v); self.width = v
    def get_height(self): return self.height
    def get_width(self): return self.width
    def get_height_maximum(self): return self._mod.height_max
    def get_width_maximum(self): return self._mod.width_max

    def set_offsetY(self, v): self._record("set_offsetY", v); self.offset_y = v
    def set_offsetX(self, v): self._record("set_offsetX", v); self.offset_x = v
    def get_offsetY_maximum(self): return self._mod.height_max - self.height
    def get_offsetX_maximum(self): return self._mod.width_max - self.width

    def set_exposure_direct(self, us):
        self._record("set_exposure_direct", us)
        # emulate hardware rounding to a coarser clock
        self.exposure_us = float(int(us // 10) * 10)

    def get_exposure(self):
        return self.exposure_us

    def set_gain_direct(self, g): self._record("set_gain_direct", g); self.gain = g

    def set_imgdataformat(self, fmt):
        self._record("set_imgdataformat", fmt)
        self.imgdataformat = fmt

    def set_output_bit_depth(self, depth): self._record("set_output_bit_depth", depth)
    def enable_output_bit_packing(self): self._record("enable_output_bit_packing",)
    def disable_aeag(self): self._record("disable_aeag",)

    # -- acquisition -----------------------------------------------------------
    def start_acquisition(self): self._record("start_acquisition",); self.acquiring = True
    def stop_acquisition(self): self._record("stop_acquisition",); self.acquiring = False

    def get_image(self, img):
        self._record("get_image",)
        if self.frames:
            img._array = self.frames.popleft()
        else:
            dtype = np.uint16 if "16" in self.imgdataformat else np.uint8
            img._array = np.zeros((self.height, self.width), dtype=dtype)

    def get_temp(self):
        return self._mod.temperature


def build_fake_ximea(serial="XIMEA0001", width_max=800, height_max=644,
                     temperature=35.0):
    """Return (ximea_package, xiapi_module) impersonating `from ximea import xiapi`."""
    xiapi_mod = types.ModuleType("ximea.xiapi")
    xiapi_mod.serial = serial
    xiapi_mod.width_max, xiapi_mod.height_max = width_max, height_max
    xiapi_mod.temperature = temperature
    xiapi_mod.cameras = []

    class Camera:
        def __new__(cls, *args, **kwargs):
            cam = FakeXiCamera(xiapi_mod)
            xiapi_mod.cameras.append(cam)
            return cam

    xiapi_mod.Camera = Camera
    xiapi_mod.Image = FakeXiImage
    xiapi_mod.last_camera = lambda: xiapi_mod.cameras[-1]

    ximea_pkg = types.ModuleType("ximea")
    ximea_pkg.xiapi = xiapi_mod
    return ximea_pkg, xiapi_mod
