<a name="v0.11.2"></a>
# [v0.11.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.2) - 12 Feb 2024

# What's Changed

## New

- Add top_kcell(s) functions and fix Instance creation [#251](https://github.com/gdsfactory/kfactory/pull/251)
- Allow inheritance from standard cells [#249](https://github.com/gdsfactory/kfactory/pull/249)
- Improve minkowski algorithms for violation fixing [#248](https://github.com/gdsfactory/kfactory/pull/248)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.1...v0.11.2


[Changes][v0.11.2]


<a name="v0.11.1"></a>
# [v0.11.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.1) - 08 Feb 2024

# What's Changed

## Bug Fixes

- Fix Layout read trying to update ports on locked cells [#244](https://github.com/gdsfactory/kfactory/pull/244)

## Dependency Updates

- Update ruff and lsp configs [#243](https://github.com/gdsfactory/kfactory/pull/243)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.0...v0.11.1


[Changes][v0.11.1]


<a name="v0.11.0"></a>
# [v0.11.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.0) - 02 Feb 2024

# What's Changed

## New

- Multi PDK [#241](https://github.com/gdsfactory/kfactory/pull/241)

## Other changes

- Version numbers [#242](https://github.com/gdsfactory/kfactory/pull/242)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.10.3...v0.11.0


[Changes][v0.11.0]


<a name="v0.10.3"></a>
# [v0.10.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.3) - 12 Jan 2024

# What's Changed

## New

- add x,y center for Cell and UMKCell [#237](https://github.com/gdsfactory/kfactory/pull/237)
- allow tuples in info and settings [#231](https://github.com/gdsfactory/kfactory/pull/231)

## Other changes

- Implement clean [#240](https://github.com/gdsfactory/kfactory/pull/240)
- Layerstack [#177](https://github.com/gdsfactory/kfactory/pull/177)
- some adjustments for layerstack [#238](https://github.com/gdsfactory/kfactory/pull/238)

## Dependency Updates

- Bump actions/setup-python from 4 to 5 [#235](https://github.com/gdsfactory/kfactory/pull/235)
- Bump actions/upload-pages-artifact from 2 to 3 [#234](https://github.com/gdsfactory/kfactory/pull/234)
- Bump actions/deploy-pages from 2 to 4 [#233](https://github.com/gdsfactory/kfactory/pull/233)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.10.2...v0.10.3


[Changes][v0.10.3]


<a name="v0.10.2"></a>
# [0.10.2 - 2023-12-08 (v0.10.2)](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.2) - 08 Dec 2023

### Fixed

- Fix no_warn being ignored in transform 

[Changes][v0.10.2]


<a name="v0.10.1"></a>
# [0.10.1 - 2023-12-05 (v0.10.1)](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.1) - 05 Dec 2023

# Added

- Added `center` to `rotate` to allow rotating around a center point 
- Added `rec_dict` to `@cell` decorator to allow for recursive dictionaries 
- Added functionality to `@cell` to allow a user defined cache 
- Added invert to `route_manhattan` and allow `routing.optical.route` to add routing_kwargs to the routing function 
- add Instance.mirror Instance.center 


# Changed

- Renamed  ->  and allow passing kwargs to set attributes of the  object 
- Renamed `function_cache` -> `cache` 
- rename autorename_ports to auto_rename_ports 
- rename port position to center 


# Fixed

- add Instance setter and getter for center [#190](https://github.com/gdsfactory/kfactory/issues/190)
- Fixed typo `enclosure_mape` -> `enclosure_map` [#211](https://github.com/gdsfactory/kfactory/issues/211)


[Changes][v0.10.1]


<a name="v0.9.0"></a>
# [v0.9.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.9.0) - 25 Sep 2023

### Added

- Added  to be set by  decorator [#180](https://github.com/gdsfactory/kfactory/issues/180)
- Added __contains__ to port and __eq__ [#182](https://github.com/gdsfactory/kfactory/issues/182)
- Add PDK capabilities to KCLayout [#171](https://github.com/gdsfactory/kfactory/pull/171) 
- Added KCell.connectivity_chek to check for port alignments and overlaps 
- Added a cli based on [typer](https://typer.tiangolo.com) to allow running of functions (taking int/float/str args) and allow upload/update of gdatasea edafiles 


### Fixed

- Fixed throw a critical log message on negative width and angles and convert them to positive ones [#183](https://github.com/gdsfactory/kfactory/issues/183)


[Changes][v0.9.0]


<a name="v0.8.0"></a>
# [v0.8.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.8.0) - 14 Jun 2023

## [v0.8.0](https://github.com/gdsfactory/kfactory/tree/0.8.0) - 2023-06-14


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

[Changes][v0.8.0]


<a name="v0.7.5"></a>
# [v0.7.5](https://github.com/gdsfactory/kfactory/releases/tag/v0.7.5) - 01 Jun 2023

# [v0.7.5](https://github.com/gdsfactory/kfactory/tree/v0.7.5) - 2023-06-01


## Added

- Added `mirror_x/mirror_y` to Instance, `xmin/xmax/ymin/ymax` getter & setter to Instance, `xmin/xmax/ymin/ymax` getter to KCell, `polygon_from_array`, `dpolygon_from_arry` [#92](https://github.com/gdsfactory/kfactory/issues/92)
- Document settings/config better [#138](https://github.com/gdsfactory/kfactory/issues/138)
- Added docs for people familiar with gdsfactory [#140](https://github.com/gdsfactory/kfactory/issues/140)


## Fixed

- Fixed missing changelog in docs [#136](https://github.com/gdsfactory/kfactory/issues/136)
- Fixed add_port ignore keep_mirror flag [#143](https://github.com/gdsfactory/kfactory/issues/143)
- Fixed changelog and changelog.d links

[Changes][v0.7.5]


<a name="v0.7.4"></a>
# [v0.7.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.7.4) - 29 May 2023

## [0.7.4](https://github.com/gdsfactory/klive/tree/0.7.4) - 2023-05-29


### Added

- add tbump and towncrier for changelog and bumping [#129](https://github.com/gdsfactory/klive/issues/129)


### Fixed

- enable non manhattan bend ports, and document how to get rid of gaps [#131](https://github.com/gdsfactory/klive/issues/131)


[Changes][v0.7.4]


<a name="v0.6.0"></a>
# [0.6.0 (v0.6.0)](https://github.com/gdsfactory/kfactory/releases/tag/v0.6.0) - 18 Apr 2023

# kcell.py
* KCell and Instance don´t  inherit from `kdb.Cell` / `kdb.Instance` anymore. They should still transparently proxy to them
* Ports automatically convert um <-> dbu
  * no more DPort/DCplxPort/ICplxPort

[Changes][v0.6.0]


<a name="v0.4.1"></a>
# [Fix (Cplx)KCell.dup (v0.4.1)](https://github.com/gdsfactory/kfactory/releases/tag/v0.4.1) - 24 Feb 2023

* `KCell` and `CplxKCell` are now properly copying their instances when copied using `dup` https://github.com/KLayout/klayout/issues/1300

[Changes][v0.4.1]


<a name="v0.4.0"></a>
# [Complex Cells (v0.4.0)](https://github.com/gdsfactory/kfactory/releases/tag/v0.4.0) - 21 Feb 2023

* `CplxKCell`:
    * Use `DCplxPort` by default. These ports can have arbitrary angle and are micrometer based
      Any other port will be silently converted to `DCplxPort`
* `library` -> `klib`:
    Rename `kf.library` -> `kf.klib`, `kf.KCell.library` -> `kf.KCell.klib`, `kf.kcell.library` -> `kf.KCell.klib` in order to not confuse with the
    KLayout library and shadow it.
    
    Put deprecation warning and remove in 0.5.0
* `autocell`
    * move cache from `cachetools.Cache[int,Any]` to a dictionary `{}`
    * deprecate cache `maxsize` for 0.5.0: this is not necessary as a dictionary has infinite size and cache eviction is unwanted
    

[Changes][v0.4.0]


[v0.11.2]: https://github.com/gdsfactory/kfactory/compare/v0.11.1...v0.11.2
[v0.11.1]: https://github.com/gdsfactory/kfactory/compare/v0.11.0...v0.11.1
[v0.11.0]: https://github.com/gdsfactory/kfactory/compare/v0.10.3...v0.11.0
[v0.10.3]: https://github.com/gdsfactory/kfactory/compare/v0.10.2...v0.10.3
[v0.10.2]: https://github.com/gdsfactory/kfactory/compare/v0.10.1...v0.10.2
[v0.10.1]: https://github.com/gdsfactory/kfactory/compare/v0.9.0...v0.10.1
[v0.9.0]: https://github.com/gdsfactory/kfactory/compare/v0.8.0...v0.9.0
[v0.8.0]: https://github.com/gdsfactory/kfactory/compare/v0.7.5...v0.8.0
[v0.7.5]: https://github.com/gdsfactory/kfactory/compare/v0.7.4...v0.7.5
[v0.7.4]: https://github.com/gdsfactory/kfactory/compare/v0.6.0...v0.7.4
[v0.6.0]: https://github.com/gdsfactory/kfactory/compare/v0.4.1...v0.6.0
[v0.4.1]: https://github.com/gdsfactory/kfactory/compare/v0.4.0...v0.4.1
[v0.4.0]: https://github.com/gdsfactory/kfactory/tree/v0.4.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.7.2 -->
