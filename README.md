# Open Source DIY Hyperspectral Imager Library
> Library to calibrate, trigger and capture data cubes for the open source DIY hyperspectral camera. 


![](https://github.com/openhsi/openhsi/actions/workflows/main.yml/badge.svg)

This Python library is licensed under the [Apache v2 License](https://www.apache.org/licenses/LICENSE-2.0). The documentation is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/3.0/au/">Creative Commons Attribution 3.0 Australia License</a>.

Documentation can be found here: [https://openhsi.github.io/openhsi/](https://openhsi.github.io/openhsi/).

## Install

`pip install openhsi`

## Requirements

- Python 3.6+
- Ximea SDK (See https://www.ximea.com/support/wiki/apis/Python)

## Development and Contributions

This whole software library, testing suite, documentation website, and PyPI package was developed in Jupyter Notebooks using [nbdev](https://nbdev.fast.ai/). 
> Info:This library is under active development and new features are still being added. 

## How to use

### Taking a single hyperspectral datacube

The example shown here uses a simulated camera for testing purposes. Replace `SimulatedCamera` with the appropriate Python class for your own camera to work with real hardware. 

```
from openhsi.capture import *

with SimulatedCamera(img_path="assets/rocky_beach.png", n_lines=1024, processing_lvl = 3) as cam:
    cam.collect()
    fig = cam.show(plot_lib="matplotlib",robust=True)
    
```

    /Users/eway/.pyenv/versions/3.8.3/lib/python3.8/site-packages/pandas/compat/__init__.py:97: UserWarning: Could not import the lzma module. Your installed Python is incomplete. Attempting to use lzma compression will result in a RuntimeError.
      warnings.warn(msg)
    100%|██████████| 1024/1024 [00:16<00:00, 60.71it/s]
    /Users/eway/.pyenv/versions/3.8.3/lib/python3.8/site-packages/requests/__init__.py:89: RequestsDependencyWarning: urllib3 (1.26.7) or chardet (3.0.4) doesn't match a supported version!
      warnings.warn("urllib3 ({}) or chardet ({}) doesn't match a supported "











    ---------------------------------------------------------------------------

    ValueError                                Traceback (most recent call last)

    <ipython-input-2-ebfdd07ee112> in <module>
          3 with SimulatedCamera(img_path="assets/rocky_beach.png", n_lines=1024, processing_lvl = 3) as cam:
          4     cam.collect()
    ----> 5     fig = cam.show(plot_lib="matplotlib",robust=True)
          6 


    ~/Desktop/openhsi/openhsi/data.py in show(self, plot_lib, red_nm, green_nm, blue_nm, robust, hist_eq)
        479         rgb /= np.max(rgb)
        480 
    --> 481     rgb_hv = hv.RGB((np.arange(rgb.shape[1]),np.arange(rgb.shape[0]),
        482                      rgb[:,:,0],rgb[:,:,1],rgb[:,:,2])).opts(width=1000,height=250,
        483                      xlabel="along-track",ylabel="cross-track",invert_yaxis=True)


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/accessors.py in pipelined_call(*args, **kwargs)
         43 
         44             try:
    ---> 45                 result = __call__(*args, **kwargs)
         46 
         47                 if not in_method:


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/accessors.py in __call__(self, *args, **kwargs)
        571                 param.main.param.warning(msg)
        572 
    --> 573         return self._dispatch_opts( *args, **kwargs)
        574 
        575     def _dispatch_opts(self, *args, **kwargs):


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/accessors.py in _dispatch_opts(self, *args, **kwargs)
        575     def _dispatch_opts(self, *args, **kwargs):
        576         if self._mode is None:
    --> 577             return self._base_opts(*args, **kwargs)
        578         elif self._mode == 'holomap':
        579             return self._holomap_opts(*args, **kwargs)


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/accessors.py in _base_opts(self, *args, **kwargs)
        654 
        655         kwargs['clone'] = False if clone is None else clone
    --> 656         return self._obj.options(*new_args, **kwargs)
    

    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/data/__init__.py in pipelined_fn(*args, **kwargs)
        203 
        204             try:
    --> 205                 result = method_fn(*args, **kwargs)
        206                 if PipelineMeta.disable:
        207                     return result


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/data/__init__.py in options(self, *args, **kwargs)
       1216     # will find them to wrap with pipeline support
       1217     def options(self, *args, **kwargs):
    -> 1218         return super(Dataset, self).options(*args, **kwargs)
       1219     options.__doc__ = Dimensioned.options.__doc__
       1220 


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/core/dimension.py in options(self, *args, **kwargs)
       1301             expanded_backends = opts._expand_by_backend(options, backend)
       1302         else:
    -> 1303             expanded_backends = [(backend, opts._expand_options(options, backend))]
       1304 
       1305         obj = self


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/util/__init__.py in _expand_options(cls, options, backend)
        376                     valid_options += group_opts.allowed_keywords
        377                 if found: continue
    --> 378                 cls._options_error(opt, objtype, backend, valid_options)
        379         return expanded
        380 


    ~/.pyenv/versions/3.8.3/lib/python3.8/site-packages/holoviews/util/__init__.py in _options_error(cls, opt, objtype, backend, valid_options)
        424                              (opt, objtype, current_backend, matches))
        425         else:
    --> 426             raise ValueError('Unexpected option %r for %s type '
        427                              'across all extensions. No similar options '
        428                              'found.' % (opt, objtype))


    ValueError: Unexpected option 'width' for RGB type across all extensions. No similar options found.

