# Release notes

<!-- do not remove -->

## 0.4.3

### New Features

- Hikrobot camera support (developed for the MV-CA013-21UM; not yet hardware-tested): `HikrobotCamera` and `SharedHikrobotCamera` in `openhsi.cameras`, built on the Hikrobot MVS SDK.

### Bugs Squashed

- Fixed `pip install` on modern setuptools (removed `pkg_resources` usage from `setup.py`).
- Pinned the nbdev toolchain (nbdev 2.3.x, `execnb<0.2`, `setuptools<81`) in CI and pre-commit so notebook export/tests run reliably again.


## 0.4.0
This bring ppssible breaking changes, for users with pickle based calibration files. Files will need to be converted.

### Bugs Squashed

- move away from pickles files in future version. ([#48](https://github.com/openhsi/openhsi/issues/48))


## 0.3.1


### Bugs Squashed

- AttributeError: 'LucidCamera' object has no attribute 'device' ([#50](https://github.com/openhsi/openhsi/issues/50))