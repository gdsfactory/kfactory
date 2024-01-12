# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/gdsfactory/kfactory/tree/main/changelog.d/>.

<!-- towncrier release notes start -->

## [0.10.3](https://github.com/gdsfactory/kfactory/releases/v0.10.3) - 2024-01-12


### Added

- Added x, y, and center properties to `KCell` and `UMKCell` [#237](https://github.com/gdsfactory/kfactory/issues/237)
- Added `KCLayout.clear`, `KCLayout.delete_cell` and other `delete_cell` functions. [#239](https://github.com/gdsfactory/kfactory/issues/239)
- Added get to meta data for KCells (info/settings) [#PR](https://github.com/gdsfactory/kfactory/pull/231) 
- Allow `Sequence` (list/tuple) types in KCell metadata (info/settings) [#PR](https://github.com/gdsfactory/kfactory/pull/231) 


### Changed

- @kf.cell can handle rebuilding deleted KCells [#239](https://github.com/gdsfactory/kfactory/issues/239)

## [0.10.2](https://github.com/gdsfactory/kfactory/releases/v0.10.2) - 2023-12-08


### Fixed

- Fix no_warn being ignored in transform 

## [0.10.1](https://github.com/gdsfactory/kfactory/releases/v0.10.1) - 2023-12-05

No significant changes.


## [0.10.0](https://github.com/gdsfactory/kfactory/releases/v0.10.0) - 2023-12-05


### Added

- Added `center` to `rotate` to allow rotating around a center point 
- Added `rec_dict` to `@cell` decorator to allow for recursive dictionaries 
- Added functionality to `@cell` to allow a user defined cache 
- Added invert to `route_manhattan` and allow `routing.optical.route` to add routing_kwargs to the routing function 
- add Instance.mirror Instance.center 


### Changed

- Renamed  ->  and allow passing kwargs to set attributes of the  object 
- Renamed `function_cache` -> `cache` 
- rename autorename_ports to auto_rename_ports 
- rename port position to center 


### Fixed

- add Instance setter and getter for center [#190](https://github.com/gdsfactory/kfactory/issues/190)
- Fixed typo `enclosure_mape` -> `enclosure_map` [#211](https://github.com/gdsfactory/kfactory/issues/211)

## [0.9.3](https://github.com/gdsfactory/kfactory/releases/v0.9.3) - 2023-10-06


### Fixed

- Fixed layer enclosure errors in extrude_path


## [0.9.2](https://github.com/gdsfactory/kfactory/releases/v0.9.2) - 2023-10-06

No significant changes.


## [0.9.1](https://github.com/gdsfactory/kfactory/releases/v0.9.1) - 2023-10-04


### Added

- Added back kf.kcell.get_cells in order to automatically scrape a module for KCell factories [PR](https://github.com/gdsfactory/kfactory/pull/187)


## [0.9.0](https://github.com/gdsfactory/kfactory/releases/v0.9.0) - 2023-09-25


### Added

- Added  to be set by  decorator [#180](https://github.com/gdsfactory/kfactory/issues/180)
- Added __contains__ to port and __eq__ [#182](https://github.com/gdsfactory/kfactory/issues/182)
- Add PDK capabilities to KCLayout [#171](https://github.com/gdsfactory/kfactory/pull/171) 
- Added KCell.connectivity_chek to check for port alignments and overlaps 
- Added a cli based on [typer](https://typer.tiangolo.com) to allow running of functions (taking int/float/str args) and allow upload/update of gdatasea edafiles 


### Fixed

- Fixed throw a critical log message on negative width and angles and convert them to positive ones [#183](https://github.com/gdsfactory/kfactory/issues/183)


## [0.8.4](https://github.com/gdsfactory/kfactory/releases/v0.8.4) - 2023-06-28


### Fixed

- Fixed name collisions for floats with long precision [#165](https://github.com/gdsfactory/kfactory/issues/165)
- Fixed port renaming by direction [#167](https://github.com/gdsfactory/kfactory/issues/167)


## [0.8.3](https://github.com/gdsfactory/kfactory/releases/v0.8.3) - 2023-06-28

No significant changes.


## [0.8.2](https://github.com/gdsfactory/kfactory/releases/v0.8.2) - 2023-06-16


### Fixed

- fix info settings


## [0.8.1](https://github.com/gdsfactory/kfactory/releases/v0.8.1) - 2023-06-16


### Fixed

- Make settings/infos in cells pydantic models and restrict types [#163](https://github.com/gdsfactory/kfactory/issues/163)
- adjust minimum version of klayout to 0.28.post2


## [0.8.0](https://github.com/gdsfactory/kfactory/releases/v0.8.0) - 2023-06-14


### Added

- KCells now store (and retrieve) Ports and settings/info in/from GDS [#106](https://github.com/gdsfactory/kfactory/issues/106)
- Added docs section about loguru config [#138](https://github.com/gdsfactory/kfactory/issues/138)
- Added docs section about gdsfactory differences [#140](https://github.com/gdsfactory/kfactory/issues/140)
- Add Netlist extraction based on klayout.db.Netlist [#147](https://github.com/gdsfactory/kfactory/issues/147)
- Added UMKCell to allow addressing some parts in um [#158](https://github.com/gdsfactory/kfactory/issues/158)
- Added snapping of ports to cell decorator [#159](https://github.com/gdsfactory/kfactory/issues/159)


### Changed

- KCell.create_inst doesn't take DCellInstArray args anymore, use KCell.d.create_inst instead [#158](https://github.com/gdsfactory/kfactory/issues/158)
- Updated the Pdk to pydantic 2.0 [PR](https://github.com/gdsfactory/kfactory/pull/157) 
- renamed waveguide -> straight [PR](https://github.com/gdsfactory/kfactory/pull/152) 


### Fixed

- Fixed incompatibility of Pdk and technology with mypy [#108](https://github.com/gdsfactory/kfactory/issues/108)
- Fixed keep_mirror flag [#143](https://github.com/gdsfactory/kfactory/issues/143)
- Fixed (ix)90° bends second port off-grid [#153](https://github.com/gdsfactory/kfactory/issues/153)
- Fixed circular and euler bends having complex ports in the x*90° cases [#159](https://github.com/gdsfactory/kfactory/issues/159)


## [0.7.5](https://github.com/gdsfactory/kfactory/releases/v0.7.5) - 2023-06-01


### Added

- Added `mirror_x/mirror_y` to Instance, `xmin/xmax/ymin/ymax` getter & setter to Instance, `xmin/xmax/ymin/ymax` getter to KCell, `polygon_from_array`, `dpolygon_from_arry` [#92](https://github.com/gdsfactory/kfactory/issues/92)
- Document settings/config better [#138](https://github.com/gdsfactory/kfactory/issues/138)
- Added docs for people familiar with gdsfactory [#140](https://github.com/gdsfactory/kfactory/issues/140)


### Fixed

- Fixed missing changelog in docs [#136](https://github.com/gdsfactory/kfactory/issues/136)
- Fixed add_port ignore keep_mirror flag [#143](https://github.com/gdsfactory/kfactory/issues/143)
- Fixed changelog and changelog.d links


## [0.7.4](https://github.com/gdsfactory/kfactory/releases/v0.7.4) - 2023-05-29


### Added

- add tbump and towncrier for changelog and bumping [#129](https://github.com/gdsfactory/kfactory/issues/129)


### Fixed

- enable non manhattan bend ports, and document how to get rid of gaps [#131](https://github.com/gdsfactory/kfactory/issues/131)
