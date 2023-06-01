# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/gdsfactory/kfactory/tree/main/changelog.d/>.

<!-- towncrier release notes start -->

## [0.7.5](https://github.com/gdsfactory/kfactory/tree/0.7.5) - 2023-06-01


### Added

- Added `mirror_x/mirror_y` to Instance, `xmin/xmax/ymin/ymax` getter & setter to Instance, `xmin/xmax/ymin/ymax` getter to KCell, `polygon_from_array`, `dpolygon_from_arry` [#92](https://github.com/gdsfactory/kfactory/issues/92)
- Document settings/config better [#138](https://github.com/gdsfactory/kfactory/issues/138)
- Added docs for people familiar with gdsfactory [#140](https://github.com/gdsfactory/kfactory/issues/140)


### Fixed

- Fixed missing changelog in docs [#136](https://github.com/gdsfactory/kfactory/issues/136)
- Fixed add_port ignore keep_mirror flag [#143](https://github.com/gdsfactory/kfactory/issues/143)
- Fixed changelog and changelog.d links


## [0.7.4](https://github.com/gdsfactory/kfactory/tree/0.7.4) - 2023-05-29


### Added

- add tbump and towncrier for changelog and bumping [#129](https://github.com/gdsfactory/kfactory/issues/129)


### Fixed

- enable non manhattan bend ports, and document how to get rid of gaps [#131](https://github.com/gdsfactory/kfactory/issues/131)
