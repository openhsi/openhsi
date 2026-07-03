"""Fake Hikrobot MVS SDK (`MvCameraControl_class`) for testing without hardware.

Mirrors exactly the call surface used by `openhsi.cameras.HikrobotCameraBase`.
The fake records every SDK call so tests can assert call ordering, and exposes
knobs for device count, serials, supported pixel formats, and queued frames.
"""

import ctypes
import types
from collections import deque

import numpy as np

# Real SDK constant values (backend only needs them to be self-consistent)
MV_GIGE_DEVICE = 0x00000020
MV_USB_DEVICE = 0x04000000
MV_ACCESS_Exclusive = 1
MV_TRIGGER_MODE_OFF = 0

MV_OK = 0
MV_E_HANDLE = 0x80000000
MV_E_SUPPORT = 0x80000001
MV_E_PARAMETER = 0x80000004
MV_E_NODATA = 0x8000000A


class _USB3V_INFO(ctypes.Structure):
    _fields_ = [("chSerialNumber", ctypes.c_ubyte * 64)]


class _GIGE_INFO(ctypes.Structure):
    _fields_ = [("chSerialNumber", ctypes.c_ubyte * 16)]


class _SPECIAL_INFO(ctypes.Union):
    _fields_ = [("stUsb3VInfo", _USB3V_INFO), ("stGigEInfo", _GIGE_INFO)]


class MV_CC_DEVICE_INFO(ctypes.Structure):
    _fields_ = [("nTLayerType", ctypes.c_uint), ("SpecialInfo", _SPECIAL_INFO)]


class MV_CC_DEVICE_INFO_LIST(ctypes.Structure):
    _fields_ = [("nDeviceNum", ctypes.c_uint), ("pDeviceInfo", ctypes.c_void_p * 256)]


class MVCC_INTVALUE(ctypes.Structure):
    _fields_ = [("nCurValue", ctypes.c_uint), ("nMax", ctypes.c_uint),
                ("nMin", ctypes.c_uint), ("nInc", ctypes.c_uint)]


class MVCC_FLOATVALUE(ctypes.Structure):
    _fields_ = [("fCurValue", ctypes.c_float), ("fMax", ctypes.c_float),
                ("fMin", ctypes.c_float)]


class MV_FRAME_OUT_INFO_EX(ctypes.Structure):
    _fields_ = [("nWidth", ctypes.c_uint), ("nHeight", ctypes.c_uint),
                ("enPixelType", ctypes.c_uint), ("nFrameNum", ctypes.c_uint),
                ("nFrameLen", ctypes.c_uint)]


def _bytes_per_pixel(pixel_format):
    return 1 if "Mono8" in pixel_format else 2


class _FakeHikCamera:
    """One fake camera handle. Node state mimics a MV-CA013-21UM-shaped device."""

    def __init__(self, module):
        self._mod = module
        self.calls = []
        self.opened = False
        self.grabbing = False
        self.device_info = None
        self.frames = deque()
        # node state
        self.ints = {
            "Width":  {"cur": module.width_max, "max": module.width_max, "min": 16, "inc": 4},
            "Height": {"cur": module.height_max, "max": module.height_max, "min": 16, "inc": 2},
            "OffsetX": {"cur": 0, "max": 0, "min": 0, "inc": 4},
            "OffsetY": {"cur": 0, "max": 0, "min": 0, "inc": 2},
        }
        self.floats = {
            "ExposureTime": module.exposure_us_default,  # microseconds
            "Gain": 0.0,
        }
        if module.has_temperature_node:
            self.floats["DeviceTemperature"] = module.temperature
        self.enums_by_string = {"PixelFormat": module.pixel_format_default,
                                "ExposureAuto": "Continuous", "GainAuto": "Continuous"}
        self.enums_by_value = {"TriggerMode": 1}

    # -- helpers ----------------------------------------------------------
    def _record(self, *call):
        self.calls.append(call)

    def _refresh_offset_limits(self):
        self.ints["OffsetX"]["max"] = self._mod.width_max - self.ints["Width"]["cur"]
        self.ints["OffsetY"]["max"] = self._mod.height_max - self.ints["Height"]["cur"]

    def queue_frame(self, array):
        """Queue a numpy array to be returned by the next frame grab."""
        self.frames.append(("array", np.ascontiguousarray(array)))

    def queue_raw(self, payload: bytes, width: int, height: int):
        """Queue raw bytes with an explicit reported width/height (e.g. packed data)."""
        self.frames.append(("raw", (payload, width, height)))

    # -- static SDK entry points ------------------------------------------
    @staticmethod
    def MV_CC_Initialize():
        return MV_OK

    # -- handle lifecycle ---------------------------------------------------
    def MV_CC_CreateHandle(self, dev_info):
        self._record("MV_CC_CreateHandle",)
        self.device_info = dev_info
        return MV_OK

    def MV_CC_OpenDevice(self, access_mode, switchover_key):
        self._record("MV_CC_OpenDevice", access_mode)
        self.opened = True
        return MV_OK

    def MV_CC_CloseDevice(self):
        self._record("MV_CC_CloseDevice",)
        self.opened = False
        return MV_OK

    def MV_CC_DestroyHandle(self):
        self._record("MV_CC_DestroyHandle",)
        return MV_OK

    # -- nodes --------------------------------------------------------------
    def MV_CC_SetEnumValue(self, name, value):
        self._record("MV_CC_SetEnumValue", name, value)
        if name.startswith("Binning") and not self._mod.supports_binning:
            return MV_E_SUPPORT
        self.enums_by_value[name] = value
        return MV_OK

    def MV_CC_SetEnumValueByString(self, name, value):
        self._record("MV_CC_SetEnumValueByString", name, value)
        if name == "PixelFormat" and value not in self._mod.supported_pixel_formats:
            return MV_E_PARAMETER
        self.enums_by_string[name] = value
        return MV_OK

    def MV_CC_SetIntValue(self, name, value):
        self._record("MV_CC_SetIntValue", name, value)
        node = self.ints.get(name)
        if node is None:
            return MV_E_SUPPORT
        if not (node["min"] <= value <= node["max"]):
            return MV_E_PARAMETER
        node["cur"] = value
        if name in ("Width", "Height"):
            self._refresh_offset_limits()
        return MV_OK

    def MV_CC_GetIntValue(self, name, val):
        self._record("MV_CC_GetIntValue", name)
        if name == "PayloadSize":
            bpp = _bytes_per_pixel(self.enums_by_string["PixelFormat"])
            cur = self.ints["Width"]["cur"] * self.ints["Height"]["cur"] * bpp
            val.nCurValue, val.nMax, val.nMin, val.nInc = cur, cur, 0, 1
            return MV_OK
        node = self.ints.get(name)
        if node is None:
            return MV_E_SUPPORT
        val.nCurValue, val.nMax, val.nMin, val.nInc = (
            node["cur"], node["max"], node["min"], node["inc"])
        return MV_OK

    def MV_CC_SetFloatValue(self, name, value):
        self._record("MV_CC_SetFloatValue", name, value)
        if name == "ExposureTime":
            # real cameras round exposure to their internal clock; emulate that
            self.floats[name] = float(round(value))
            return MV_OK
        if name in self.floats or name == "Gain":
            self.floats[name] = float(value)
            return MV_OK
        return MV_E_SUPPORT

    def MV_CC_GetFloatValue(self, name, val):
        self._record("MV_CC_GetFloatValue", name)
        if name not in self.floats:
            return MV_E_SUPPORT
        val.fCurValue = self.floats[name]
        return MV_OK

    # -- acquisition ----------------------------------------------------------
    def MV_CC_StartGrabbing(self):
        self._record("MV_CC_StartGrabbing",)
        self.grabbing = True
        return MV_OK

    def MV_CC_StopGrabbing(self):
        self._record("MV_CC_StopGrabbing",)
        self.grabbing = False
        return MV_OK

    def MV_CC_GetOneFrameTimeout(self, pdata, size, frame_info, timeout_ms):
        self._record("MV_CC_GetOneFrameTimeout", size, timeout_ms)
        width = self.ints["Width"]["cur"]
        height = self.ints["Height"]["cur"]
        if self.frames:
            kind, item = self.frames.popleft()
            if kind == "array":
                payload = item.tobytes()
                height, width = item.shape
            else:
                payload, width, height = item
        else:
            bpp = _bytes_per_pixel(self.enums_by_string["PixelFormat"])
            payload = bytes(width * height * bpp)
        if len(payload) > size:
            return MV_E_PARAMETER
        ctypes.memmove(pdata, payload, len(payload))
        frame_info.nWidth, frame_info.nHeight = width, height
        frame_info.nFrameLen = len(payload)
        return MV_OK


def build_fake_mvs(serials=("DA1234567",), tlayer_types=None, width_max=1280,
                   height_max=1024,
                   supported_pixel_formats=("Mono8", "Mono10", "Mono12"),
                   pixel_format_default="Mono8", supports_binning=False,
                   temperature=42.5, has_temperature_node=True,
                   exposure_us_default=10000.0, with_initialize=True):
    """Build a module object impersonating `MvCameraControl_class`."""
    mod = types.ModuleType("MvCameraControl_class")
    mod.__dict__.update(
        MV_GIGE_DEVICE=MV_GIGE_DEVICE, MV_USB_DEVICE=MV_USB_DEVICE,
        MV_ACCESS_Exclusive=MV_ACCESS_Exclusive,
        MV_TRIGGER_MODE_OFF=MV_TRIGGER_MODE_OFF,
        MV_CC_DEVICE_INFO=MV_CC_DEVICE_INFO,
        MV_CC_DEVICE_INFO_LIST=MV_CC_DEVICE_INFO_LIST,
        MVCC_INTVALUE=MVCC_INTVALUE, MVCC_FLOATVALUE=MVCC_FLOATVALUE,
        MV_FRAME_OUT_INFO_EX=MV_FRAME_OUT_INFO_EX,
    )
    mod.width_max, mod.height_max = width_max, height_max
    mod.supported_pixel_formats = tuple(supported_pixel_formats)
    mod.pixel_format_default = pixel_format_default
    mod.supports_binning = supports_binning
    mod.temperature = temperature
    mod.has_temperature_node = has_temperature_node
    mod.exposure_us_default = exposure_us_default
    mod.cameras = []           # every _FakeHikCamera constructed
    mod.initialize_calls = 0

    # Build the device table (kept alive on the module: ctypes pointers don't own)
    if tlayer_types is None:
        tlayer_types = [MV_USB_DEVICE] * len(serials)
    mod._device_structs = []
    for serial, tlayer in zip(serials, tlayer_types):
        info = MV_CC_DEVICE_INFO()
        info.nTLayerType = tlayer
        field = (info.SpecialInfo.stUsb3VInfo.chSerialNumber
                 if tlayer == MV_USB_DEVICE
                 else info.SpecialInfo.stGigEInfo.chSerialNumber)
        raw = serial.encode()
        field[:len(raw)] = raw
        mod._device_structs.append(info)

    class MvCamera:
        def __new__(cls, *args, **kwargs):
            cam = _FakeHikCamera(mod)
            mod.cameras.append(cam)
            return cam

        @staticmethod
        def MV_CC_EnumDevices(tlayer_mask, dev_list):
            matching = [d for d in mod._device_structs if d.nTLayerType & tlayer_mask]
            dev_list.nDeviceNum = len(matching)
            for i, dev in enumerate(matching):
                dev_list.pDeviceInfo[i] = ctypes.cast(
                    ctypes.pointer(dev), ctypes.c_void_p)
            return MV_OK

    if with_initialize:
        def _initialize():
            mod.initialize_calls += 1
            return MV_OK
        MvCamera.MV_CC_Initialize = staticmethod(_initialize)

    mod.MvCamera = MvCamera
    mod.last_camera = lambda: mod.cameras[-1]
    return mod
