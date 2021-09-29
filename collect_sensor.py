from openhsi import *
from openhsi.calibrate import *
from openhsi.capture import *
from openhsi.utils import *
from openhsi.sensors import *

import xarray as xr
import numpy as np
import pandas as pd
import datetime
import time
import pickle

from pathlib import Path

import Jetson.GPIO as GPIO


peripherals = SensorStream(baudrate=921_600,port="/dev/ttyTHS0")
peripherals.run() # start on switch on, pause on switch off, KeyboardInterrupt to stop
