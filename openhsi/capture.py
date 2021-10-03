# AUTOGENERATED! DO NOT EDIT! File to edit: 01_capture.ipynb (unless otherwise specified).

__all__ = ['OpenHSI', 'cam', 'SimulatedCamera', 'XimeaCamera']

# Cell

from fastcore.foundation import patch
from fastcore.meta import delegates
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from scipy.interpolate import interp1d
from PIL import Image
from tqdm import tqdm
from ximea import xiapi

from typing import Iterable, Union, Callable, List, TypeVar, Generic, Tuple, Optional
import json
import pickle

# Cell

from .data import *


# Cell

@delegates()
class OpenHSI(DataCube):
    """Base Class for the OpenHSI Camera."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        super().set_processing_lvl(self.proc_lvl)

    def __enter__(self):
        return self

    def __close__(self):
        self.stop_cam()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_cam()

    def collect(self):
        """Collect the hyperspectral datacube."""
        self.start_cam()
        for i in tqdm(range(self.n_lines)):
            self.put(self.get_img())
        self.stop_cam()

cam = OpenHSI()

# Cell

@delegates()
class SimulatedCamera(OpenHSI):

    def __init__(self, img_path:str = None, **kwargs):
        """Initialise Simulated Camera"""
        super().__init__(**kwargs)

        if img_path is None:
            self.img = np.random.randint(0,255,(*self.settings["resolution"],3))
        else:
            with Image.open(img_path) as img:
                img = img.resize((np.shape(img)[1],self.settings["resolution"][0]))
                self.img = np.array(img)

        self.rgb_buff = CircArrayBuffer(self.img.shape,axis=1,dtype=np.uint8)
        self.rgb_buff.data = self.img
        self.rgb_buff.slots_left = 0 # make buffer full

        # Precompute the CIE XYZ matching functions to convert RGB values to a pseudo-spectra
        def piecewise_Guass(x,A,μ,σ1,σ2):
            t = (x-μ) / ( σ1 if x < μ else σ2 )
            return A * np.exp( -(t**2)/2 )
        def wavelength2xyz(λ):
            """λ is in nanometers"""
            λ *= 10 # convert to angstroms for the below formulas
            x̅ = piecewise_Guass(λ,  1.056, 5998, 379, 310) + \
                piecewise_Guass(λ,  0.362, 4420, 160, 267) + \
                piecewise_Guass(λ, -0.065, 5011, 204, 262)
            y̅ = piecewise_Guass(λ,  0.821, 5688, 469, 405) + \
                piecewise_Guass(λ,  0.286, 5309, 163, 311)
            z̅ = piecewise_Guass(λ,  1.217, 4370, 118, 360) + \
                piecewise_Guass(λ,  0.681, 4590, 260, 138)
            return np.array([x̅,y̅,z̅])
        self.xs = np.zeros( (1,self.settings["resolution"][1]),dtype=np.float32)
        self.ys = self.xs.copy(); self.zs = self.xs.copy()
        self.λs = np.linspace(*self.settings["index2wavelength_range"][:2],num=self.settings["resolution"][1])
        for i in range(len(self.xs[0])):
            self.xs[0,i], self.ys[0,i], self.zs[0,i] = wavelength2xyz(self.λs[i])

        self.xyz_buff = CircArrayBuffer(self.settings["resolution"],axis=0,dtype=np.int32)

    def rgb2xyz_matching_funcs(self, rgb:np.ndarray) -> np.ndarray:
        """convert an RGB value to a pseudo-spectra with the CIE XYZ matching functions."""
        for i in range(rgb.shape[0]):
            self.xyz_buff.put( rgb[i,0]*self.xs + rgb[i,1]*self.ys + rgb[i,2]*self.zs )
        return self.xyz_buff.data

    def start_cam(self):
        pass

    def stop_cam(self):
        pass

    def get_img(self) -> np.ndarray:
        if self.rgb_buff.is_empty():
            self.rgb_buff.slots_left = 0 # make buffer full again
        return self.rgb2xyz_matching_funcs(self.rgb_buff.get())


with SimulatedCamera(img_path="assets/rocky_beach.png", n_lines=1024, processing_lvl = 3) as cam:
    cam.collect()
    fig = cam.show(robust=True)

fig


# Cell


@delegates
class XimeaCamera(OpenHSI):
    """Core functionality for Ximea cameras"""
    # https://www.ximea.com/support/wiki/apis/Python
    def __init__(self,**kwargs):
        """Initialise Camera"""

        super().__init__(**kwargs)

        self.xicam = xiapi.Camera()
        self.xicam.open_device_by_SN(serial_number) if serial_number else self.xicam.open_device()

        print(f'Connected to device {self.xicam.get_device_sn()}')

        self.xbinwidth  = xbinwidth
        self.xbinoffset = xbinoffset
        self.exposure   = exposure_ms
        self.gain       = 0

        self.xicam.set_width(self.xbinwidth)
        self.xicam.set_offsetX(self.xbinoffset)
        self.xicam.set_exposure_direct(1000*self.exposure)
        self.xicam.set_gain_direct(self.gain)

        self.xicam.set_imgdataformat("XI_RAW16")
        self.xicam.set_output_bit_depth("XI_BPP_12")
        self.xicam.enable_output_bit_packing()
        self.xicam.disable_aeag()

        self.xicam.set_binning_vertical(2)
        self.xicam.set_binning_vertical_mode("XI_BIN_MODE_SUM")

        self.rows, self.cols = self.xicam.get_height(), self.xicam.get_width()
        self.img = xiapi.Image()

        self.load_cam_settings()

    def start_cam(self):
        self.xicam.start_acquisition()

    def stop_cam(self):
        self.xicam.stop_acquisition()
        self.xicam.close_device()

    def get_img(self) -> np.ndarray:
        self.xicam.get_image(self.img)
        return self.img.get_image_data_numpy()