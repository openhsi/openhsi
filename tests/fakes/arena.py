"""Fake Lucid Vision Arena SDK (`arena_api`) mirroring the surface used by
LucidCameraBase, including buffers for the Mono8/Mono12-packed/Mono16 decode
branches of `get_img`."""

import ctypes
import types
from collections import deque

import numpy as np


class DeviceNotFoundError(Exception):
    """arena_api raises this from create_device when no camera is connected."""


class _Node:
    def __init__(self, value, vmax=None, vmin=None):
        self._value = value
        self.max = vmax
        self.min = vmin

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        self._value = v


class _NodeMap(dict):
    def get_node(self, names):
        return {name: self[name] for name in names}


def pack_mono12(pixels: np.ndarray) -> bytes:
    """Inverse of LucidCameraBase.get_img's 12-bit unpacking:
    fst = (b0<<4)+(b1>>4);  snd = (b2<<4)+(b1&15)."""
    flat = pixels.astype(np.uint16).ravel()
    assert len(flat) % 2 == 0, "12-bit packing needs an even pixel count"
    out = bytearray()
    for p0, p1 in zip(flat[0::2], flat[1::2]):
        out.append((int(p0) >> 4) & 0xFF)
        out.append(((int(p0) & 0xF) << 4) | (int(p1) & 0xF))
        out.append((int(p1) >> 4) & 0xFF)
    return bytes(out)


class FakeArenaBuffer:
    def __init__(self, array: np.ndarray, bits_per_pixel: int):
        self.bits_per_pixel = bits_per_pixel
        self.height, self.width = array.shape
        if bits_per_pixel == 8:
            payload = array.astype(np.uint8).tobytes()
        elif bits_per_pixel in (10, 12):
            payload = pack_mono12(array)
        elif bits_per_pixel == 16:
            payload = array.astype(np.uint16).tobytes()
        else:
            raise ValueError(f"unsupported bits_per_pixel {bits_per_pixel}")
        self.buffer_size = len(payload)
        self._backing = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
        self.pdata = ctypes.cast(self._backing, ctypes.POINTER(ctypes.c_ubyte))


class FakeArenaDevice:
    def __init__(self, module):
        self._mod = module
        self.calls = []
        self.streaming = False
        self.frames = deque()
        self.tl_stream_nodemap = _NodeMap({
            "StreamAutoNegotiatePacketSize": _Node(False),
            "StreamPacketResendEnable": _Node(False),
        })
        wmax, hmax = module.width_max, module.height_max
        self.nodemap = _NodeMap({
            "AcquisitionFrameRate": _Node(10.0, vmax=module.framerate_max, vmin=0.1),
            "AcquisitionFrameRateEnable": _Node(False),
            "AcquisitionMode": _Node("Continuous"),
            "AcquisitionStart": _Node(None),
            "AcquisitionStop": _Node(None),
            "BinningHorizontal": _Node(1),
            "BinningVertical": _Node(1),
            "DevicePower": _Node(0),
            "DeviceTemperature": _Node(module.temperature),
            "DeviceUpTime": _Node(0),
            "DeviceUserID": _Node("FakeLucid"),
            "ExposureAuto": _Node("Continuous"),
            "ExposureTime": _Node(10000.0, vmax=1e7, vmin=module.exposure_min_us),
            "Gain": _Node(0.0),
            "GammaEnable": _Node(True),
            "Height": _Node(hmax, vmax=hmax, vmin=16),
            "OffsetX": _Node(0, vmax=0, vmin=0),
            "OffsetY": _Node(0, vmax=0, vmin=0),
            "PixelFormat": _Node("Mono8"),
            "ReverseX": _Node(False),
            "ReverseY": _Node(False),
            "Width": _Node(wmax, vmax=wmax, vmin=16),
            "GevMACAddress": _Node(0x1C0FAF017BA0),
            "DeviceSerialNumber": _Node(module.serial),
        })

    def queue_frame(self, array):
        self.frames.append(np.asarray(array))

    def start_stream(self, n):
        self.calls.append(("start_stream", n))
        self.streaming = True

    def stop_stream(self):
        self.calls.append(("stop_stream",))
        self.streaming = False

    def get_buffer(self):
        self.calls.append(("get_buffer",))
        bpp_by_format = {"Mono8": 8, "Mono10": 10, "Mono12": 12,
                         "Mono12Packed": 12, "Mono10Packed": 10, "Mono16": 16}
        bpp = bpp_by_format.get(self.nodemap["PixelFormat"].value, 12)
        if self.frames:
            frame = self.frames.popleft()
        else:
            frame = np.zeros((self.nodemap["Height"].value,
                              self.nodemap["Width"].value), dtype=np.uint16)
        return FakeArenaBuffer(frame, bpp)

    def requeue_buffer(self, buf):
        self.calls.append(("requeue_buffer",))


class FakeArenaSystem:
    def __init__(self, module):
        self._mod = module
        self.calls = []

    @property
    def device_infos(self):
        if self._mod.n_devices == 0:
            return []
        return [{"serial": self._mod.serial}]

    def destroy_device(self):
        self.calls.append(("destroy_device",))

    def create_device(self, device_infos=None):
        self.calls.append(("create_device",))
        if self._mod.n_devices == 0:
            raise DeviceNotFoundError("No arena devices found")
        dev = FakeArenaDevice(self._mod)
        self._mod.devices.append(dev)
        return [dev]


def build_fake_arena(n_devices=1, serial="LUCID0001", width_max=1440,
                     height_max=1080, temperature=30.0, framerate_max=100.0,
                     exposure_min_us=20.0):
    """Return (arena_api_pkg, system_module) impersonating
    `from arena_api.system import system`."""
    state = types.ModuleType("arena_api")
    state.n_devices = n_devices
    state.serial = serial
    state.width_max, state.height_max = width_max, height_max
    state.temperature = temperature
    state.framerate_max = framerate_max
    state.exposure_min_us = exposure_min_us
    state.devices = []
    state.DeviceNotFoundError = DeviceNotFoundError

    system_mod = types.ModuleType("arena_api.system")
    system_mod.system = FakeArenaSystem(state)

    state.system = system_mod
    state.last_device = lambda: state.devices[-1]
    return state, system_mod
