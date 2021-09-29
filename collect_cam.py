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


run_collect = Collector()
run_collect.run(n=2048)

