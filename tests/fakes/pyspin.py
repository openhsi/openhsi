"""Fake `simple_pyspin` (FLIR) mirroring the surface used by FlirCameraBase.

Nodes are plain attributes (that is how simple_pyspin exposes GenICam nodes),
so the fake keeps a node dict behind __getattr__/__setattr__. The node set is
configurable per camera generation, because FlirCameraBase's whole job is
handling the naming differences (e.g. AcquisitionFrameRateEnable vs
...Enabled).
"""

import types
from collections import deque

import numpy as np

# Node names by camera generation (the ones FlirCameraBase touches)
BFS_NODES = {
    "GainAuto": "Off", "Gain": 0.0,
    "AcquisitionFrameRateEnable": False, "AcquisitionFrameRate": 30,
    "ExposureAuto": "Off", "ExposureTime": 10000.0,
    "GammaEnable": True,
    "Width": None, "Height": None, "OffsetX": 0, "OffsetY": 0,
    "DeviceTemperature": 25.0,
    "ExposureMin": 20.0,
}
GS3_NODES = {
    "GainAuto": "Off", "Gain": 0.0,
    "AcquisitionFrameRateAuto": "Off",
    "AcquisitionFrameRateEnabled": False, "AcquisitionFrameRate": 30,
    "ExposureAuto": "Off", "ExposureTime": 10000.0,
    "GammaEnabled": True,
    "Width": None, "Height": None, "OffsetX": 0, "OffsetY": 0,
    "DeviceTemperature": 25.0,
    "ExposureMinAbsVal_Float": 19.0,
}


class FakeFlirCamera:
    _internal = ("_nodes", "calls", "frames", "initialized", "running",
                 "SensorWidth", "SensorHeight", "camera_node_types",
                 "_init_delay")

    def __init__(self, nodes, sensor_width, sensor_height, init_delay=0):
        object.__setattr__(self, "_nodes", dict(nodes))
        object.__setattr__(self, "calls", [])
        object.__setattr__(self, "frames", deque())
        object.__setattr__(self, "initialized", False)
        object.__setattr__(self, "running", False)
        object.__setattr__(self, "SensorWidth", sensor_width)
        object.__setattr__(self, "SensorHeight", sensor_height)
        object.__setattr__(self, "camera_node_types",
                           {name: type(v).__name__ for name, v in nodes.items()})
        object.__setattr__(self, "_init_delay", init_delay)
        self._nodes.setdefault("Width", sensor_width)
        self._nodes.setdefault("Height", sensor_height)

    # attribute-style node access, as simple_pyspin does
    def __getattr__(self, name):
        nodes = object.__getattribute__(self, "_nodes")
        if name in nodes:
            return nodes[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name in self._internal:
            object.__setattr__(self, name, value)
            return
        nodes = object.__getattribute__(self, "_nodes")
        if name not in nodes:
            raise AttributeError(f"camera has no node {name}")
        nodes[name] = value
        object.__getattribute__(self, "calls").append(("set", name, value))

    # -- lifecycle -----------------------------------------------------------
    def init(self):
        self.calls.append(("init",))
        if self._init_delay > 0:
            # camera not immediately initialized; FlirCameraBase polls with sleep()
            object.__setattr__(self, "_init_delay", self._init_delay - 1)
        else:
            object.__setattr__(self, "initialized", True)

    def start(self):
        self.calls.append(("start",))
        object.__setattr__(self, "running", True)

    def stop(self):
        self.calls.append(("stop",))
        object.__setattr__(self, "running", False)

    def close(self):
        self.calls.append(("close",))

    # -- frames ---------------------------------------------------------------
    def queue_frame(self, array):
        self.frames.append(np.asarray(array))

    def get_array(self):
        self.calls.append(("get_array",))
        if self.frames:
            return self.frames.popleft()
        return np.zeros((self._nodes["Height"], self._nodes["Width"]),
                        dtype=np.uint16)


def build_fake_flir(style="BFS", sensor_width=1440, sensor_height=1080,
                    init_delay=0):
    """Return a module impersonating `simple_pyspin` with the given node style."""
    mod = types.ModuleType("simple_pyspin")
    nodes = BFS_NODES if style == "BFS" else GS3_NODES
    mod.cameras = []

    class Camera:
        def __new__(cls, *args, **kwargs):
            cam = FakeFlirCamera(nodes, sensor_width, sensor_height,
                                 init_delay=init_delay)
            mod.cameras.append(cam)
            return cam

    mod.Camera = Camera
    mod.last_camera = lambda: mod.cameras[-1]
    return mod
