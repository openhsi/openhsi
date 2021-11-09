# Setup up Python enviroment

We recommend miniconda (https://docs.conda.io/en/latest/miniconda.html) or Miniforge (https://github.com/conda-forge/miniforge) as the base eniviroment for minimal effort. However any modern python install (py>3.6) should work.

## Setup via conda
Install all python dependancies for OpenHSI (excepts cameras) and 6SV.

    conda env create -f environment.yml

## Setup via pip

    pip install openhsi

### Install 6SV

    git clone https://github.com/robintw/6S.git
    cd 6S
    cmake -D CMAKE_INSTALL_PREFIX=/usr/local .


## Install LUCIDVISION SDK (Sydney Photonics OpenHSI)



## Weird Specific things using some cameras

### fix ximea thread warning

    sudo setcap cap_sys_nice+ep readlink -f $(which python)
    sudo setcap cap_sys_nice+ep readlink -f $(which jupyter)