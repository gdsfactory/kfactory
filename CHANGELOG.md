<a name="v0.17.2"></a>
# [v0.17.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.2) - 09 Jun 2024

# What's Changed

## New

- Add functional `check_ports` to `@cell` decorators [#389](https://github.com/gdsfactory/kfactory/pull/389)

## Bug Fixes

- fix routing issues with bounding boxes [#388](https://github.com/gdsfactory/kfactory/pull/388)
- fix cases in bundle routing [#387](https://github.com/gdsfactory/kfactory/pull/387)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.1...v0.17.2


[Changes][v0.17.2]


<a name="v0.17.1"></a>
# [v0.17.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.1) - 08 Jun 2024

# What's Changed

## New

- add to_um and to_dbu into KCLayout [#380](https://github.com/gdsfactory/kfactory/pull/380)
- add `func.__name__` for partials [#378](https://github.com/gdsfactory/kfactory/pull/378)

## Bug Fixes

- fix plot with vinsts [#385](https://github.com/gdsfactory/kfactory/pull/385)
- pass flags to connect [#384](https://github.com/gdsfactory/kfactory/pull/384)
- Fix dcplx_trans setter on Port [#383](https://github.com/gdsfactory/kfactory/pull/383)
- Fix cells duplicated by  having settings and info [#379](https://github.com/gdsfactory/kfactory/pull/379)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.0...v0.17.1


[Changes][v0.17.1]


<a name="v0.17.0"></a>
# [v0.17.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.0) - 05 Jun 2024

# What's Changed

## Breaking

- Drop rec_dicts flag and make it default to use rec dict inspection [#375](https://github.com/gdsfactory/kfactory/pull/375)

## Bug Fixes

- Improve and fix enclosure_tiled for KCellEnclosure and LayerEnclosure [#374](https://github.com/gdsfactory/kfactory/pull/374)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.16.1...v0.17.0


[Changes][v0.17.0]


<a name="v0.16.1"></a>
# [v0.16.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.16.1) - 02 Jun 2024

# What's Changed

## New

- Improve logger [#368](https://github.com/gdsfactory/kfactory/pull/368)

## Bug Fixes

- fix locked cell error [#367](https://github.com/gdsfactory/kfactory/pull/367)

## Documentation

- Improve logger [#368](https://github.com/gdsfactory/kfactory/pull/368)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.16.0...v0.16.1


[Changes][v0.16.1]


<a name="v0.16.0"></a>
# [v0.16.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.16.0) - 02 Jun 2024

# What's Changed

## Breaking

- `mirror` and `dmirror` M90 by default [#350](https://github.com/gdsfactory/kfactory/pull/350)

## New

- Add `overwrite_existing` and `layout_cache` options to the cell decorator [#362](https://github.com/gdsfactory/kfactory/pull/362)
- Better error prints [#366](https://github.com/gdsfactory/kfactory/pull/366)
- Add length and length_straights to OpticalAllAngleRoute [#361](https://github.com/gdsfactory/kfactory/pull/361)
- Add all easy access properties to VKCell and VInstance [#360](https://github.com/gdsfactory/kfactory/pull/360)
- Add lyrdb option to `plot` [#359](https://github.com/gdsfactory/kfactory/pull/359)
- Improve all-angle route_bundle to allow no backbone [#353](https://github.com/gdsfactory/kfactory/pull/353)
- Add hash to long automatic cell name [#346](https://github.com/gdsfactory/kfactory/pull/346)
- `mirror` and `dmirror` M90 by default [#350](https://github.com/gdsfactory/kfactory/pull/350)

## Bug Fixes

- fix dy for VInstance [#365](https://github.com/gdsfactory/kfactory/pull/365)
- typo [#364](https://github.com/gdsfactory/kfactory/pull/364)
- fix virtual cell show hierarchy error [#358](https://github.com/gdsfactory/kfactory/pull/358)
- Fix VKCell Setting Units [#355](https://github.com/gdsfactory/kfactory/pull/355)
- fix typo [#351](https://github.com/gdsfactory/kfactory/pull/351)
- Improve drotate [#349](https://github.com/gdsfactory/kfactory/pull/349)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.15.2...v0.16.0


[Changes][v0.16.0]


<a name="v0.15.2"></a>
# [v0.15.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.2) - 29 May 2024

# What's Changed

## Bug Fixes

- fix global config settings only being set on first import [#345](https://github.com/gdsfactory/kfactory/pull/345)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.15.1...v0.15.2


[Changes][v0.15.2]


<a name="v0.15.1"></a>
# [v0.15.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.1) - 29 May 2024

# What's Changed

## New

- Add `multi` option to fill and fix bugs [#344](https://github.com/gdsfactory/kfactory/pull/344)
- add route_width to `optical.route` [#342](https://github.com/gdsfactory/kfactory/pull/342)
- Add enum for handling check_instances [#341](https://github.com/gdsfactory/kfactory/pull/341)
- add center to SizeInfo [#340](https://github.com/gdsfactory/kfactory/pull/340)

## Bug Fixes

- Add `multi` option to fill and fix bugs [#344](https://github.com/gdsfactory/kfactory/pull/344)
- fix basename and function_name metainfo [#343](https://github.com/gdsfactory/kfactory/pull/343)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.15.0...v0.15.1


[Changes][v0.15.1]


<a name="v0.15.0"></a>
# [v0.15.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.0) - 27 May 2024

# What's Changed

## Breaking

- Change to  `d{key}` instead of `d.{key}` [#339](https://github.com/gdsfactory/kfactory/pull/339)

## New

- Add `route_smart` and `route_bundle` port sort [#335](https://github.com/gdsfactory/kfactory/pull/335)

## Bug Fixes

- Fix metaformat [#338](https://github.com/gdsfactory/kfactory/pull/338)
- Fix single bundle case for route_bundle [#337](https://github.com/gdsfactory/kfactory/pull/337)
- Fix route_bundle requiring a non-empty list of bounding boxes [#336](https://github.com/gdsfactory/kfactory/pull/336)

## Documentation

- Change to  `d{key}` instead of `d.{key}` [#339](https://github.com/gdsfactory/kfactory/pull/339)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.14.0...v0.15.0


[Changes][v0.15.0]


<a name="v0.14.0"></a>
# [v0.14.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.14.0) - 24 May 2024

# What's Changed

## New

- Add global flags for connection to not carry over rotation or angle [#332](https://github.com/gdsfactory/kfactory/pull/332)
- Separate function name [#331](https://github.com/gdsfactory/kfactory/pull/331)
- allow new conf fields [#325](https://github.com/gdsfactory/kfactory/pull/325)

## Bug Fixes

- Fix all angle bundle router [#334](https://github.com/gdsfactory/kfactory/pull/334)
- fix add port [#326](https://github.com/gdsfactory/kfactory/pull/326)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.3...v0.14.0


[Changes][v0.14.0]


<a name="v0.13.3"></a>
# [v0.13.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.3) - 21 May 2024

# What's Changed

## New

- add clear_kcells [#324](https://github.com/gdsfactory/kfactory/pull/324)
- add write configs and connection behavior [#323](https://github.com/gdsfactory/kfactory/pull/323)
- add instance.size_info [#317](https://github.com/gdsfactory/kfactory/pull/317)

## Bug Fixes

- ports in instance [#316](https://github.com/gdsfactory/kfactory/pull/316)

## Documentation

- rename allow_width_mismatch [#319](https://github.com/gdsfactory/kfactory/pull/319)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.2...v0.13.3


[Changes][v0.13.3]


<a name="v0.13.2"></a>
# [v0.13.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.2) - 15 May 2024

# What's Changed

## New

- Improve fill tiled with row/column vectors [#314](https://github.com/gdsfactory/kfactory/pull/314)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.1...v0.13.2

[Changes][v0.13.2]


<a name="v0.13.1"></a>
# [v0.13.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.1) - 15 May 2024

# What's Changed

## Bug Fixes

- fix grid instance array not properly setting up the array [#310](https://github.com/gdsfactory/kfactory/pull/310)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.0...v0.13.1


[Changes][v0.13.1]


<a name="v0.13.0"></a>
# [v0.13.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.0) - 07 May 2024

# What's Changed

## New

- Improve VKCell/VInstance [#305](https://github.com/gdsfactory/kfactory/pull/305)
- allow_different_port_widths for electrical routing [#307](https://github.com/gdsfactory/kfactory/pull/307)
- add minimum_straight [#304](https://github.com/gdsfactory/kfactory/pull/304)
- add inside flag to route_loopback [#303](https://github.com/gdsfactory/kfactory/pull/303)
- Add optional  type for settings to KCell to annotate units of parameters [#302](https://github.com/gdsfactory/kfactory/pull/302)
- Add indirect routing of endpoints [#301](https://github.com/gdsfactory/kfactory/pull/301)
- Allow dicts in info [#293](https://github.com/gdsfactory/kfactory/pull/293)
- Add smart routing [#295](https://github.com/gdsfactory/kfactory/pull/295)
- Add (ly)rdb and l2n to show [#296](https://github.com/gdsfactory/kfactory/pull/296)
- Add filter orientation [#291](https://github.com/gdsfactory/kfactory/pull/291)
- print ports in um [#289](https://github.com/gdsfactory/kfactory/pull/289)
- return uminstance with moving references [#287](https://github.com/gdsfactory/kfactory/pull/287)
- Add post process [#273](https://github.com/gdsfactory/kfactory/pull/273)
- serialize settings [#285](https://github.com/gdsfactory/kfactory/pull/285)
- Fix routing issues [#284](https://github.com/gdsfactory/kfactory/pull/284)
- Add `copy_polar` to `Port` [#282](https://github.com/gdsfactory/kfactory/pull/282)

## Bug Fixes

- `pprint_ports` add missing type switch [#306](https://github.com/gdsfactory/kfactory/pull/306)
- Fix route_smart ignoring bounding boxes at the end of the routes [#309](https://github.com/gdsfactory/kfactory/pull/309)
- Fix passing port_type to route_single [#298](https://github.com/gdsfactory/kfactory/pull/298)
- fix flatten [#300](https://github.com/gdsfactory/kfactory/pull/300)
- fix typos [#292](https://github.com/gdsfactory/kfactory/pull/292)
- fix invert for route_manhattan [#288](https://github.com/gdsfactory/kfactory/pull/288)
- Fix routing issues [#284](https://github.com/gdsfactory/kfactory/pull/284)
- Fix proxy KCells [#278](https://github.com/gdsfactory/kfactory/pull/278)
- fix manahattan router terminating routing too early [#275](https://github.com/gdsfactory/kfactory/pull/275)

## Documentation

- Implement protocols for routing functions [#280](https://github.com/gdsfactory/kfactory/pull/280)

## Dependency Updates

- Ruff formatting [#279](https://github.com/gdsfactory/kfactory/pull/279)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.12.3...v0.13.0


[Changes][v0.13.0]


<a name="v0.12.3"></a>
# [v0.12.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.3) - 06 Mar 2024

# What's Changed

## Bug Fixes

- Fix KCellEnclosure and rename bbox_per_layer to bbox [#270](https://github.com/gdsfactory/kfactory/pull/270)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.12.2...v0.12.3


[Changes][v0.12.3]


<a name="v0.12.2"></a>
# [v0.12.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.2) - 06 Mar 2024

# What's Changed

## Bug Fixes

- Fix initialization of KCLayout.constants [#269](https://github.com/gdsfactory/kfactory/pull/269)
- Fix factories for euler and taper [#268](https://github.com/gdsfactory/kfactory/pull/268)
- fix KCLayout not allowing constants in the constructor [#267](https://github.com/gdsfactory/kfactory/pull/267)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.12.0...v0.12.2


[Changes][v0.12.2]


<a name="v0.12.0"></a>
# [v0.12.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.0) - 01 Mar 2024

# What's Changed

## Breaking

- Refactor cells classes into functions with protocols [#263](https://github.com/gdsfactory/kfactory/pull/263)

## New

- Move `@vcell` to KCLayout [#264](https://github.com/gdsfactory/kfactory/pull/264)
- Add 'additional_info' to constructor for standard cells [#262](https://github.com/gdsfactory/kfactory/pull/262)

## Documentation

- Refactor cells classes into functions with protocols [#263](https://github.com/gdsfactory/kfactory/pull/263)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.4...v0.12.0


[Changes][v0.12.0]


<a name="v0.11.4"></a>
# [v0.11.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.4) - 28 Feb 2024

# What's Changed

## New

- Add automatic registering of KCell-functions to the KCLayout.factories [#261](https://github.com/gdsfactory/kfactory/pull/261)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.3...v0.11.4


[Changes][v0.11.4]


<a name="v0.11.3"></a>
# [v0.11.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.3) - 27 Feb 2024

# What's Changed

## New

- KCLayout cell decorator [#260](https://github.com/gdsfactory/kfactory/pull/260)
- Implement Grid [#255](https://github.com/gdsfactory/kfactory/pull/255)
- Add port access for instance arrays and pretty print for ports [#252](https://github.com/gdsfactory/kfactory/pull/252)

## Bug Fixes

- Fix tiling border problems [#256](https://github.com/gdsfactory/kfactory/pull/256)

## Documentation

- KCLayout cell decorator [#260](https://github.com/gdsfactory/kfactory/pull/260)

## Dependency Updates

- update min klayout version [#254](https://github.com/gdsfactory/kfactory/pull/254)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.2...v0.11.3


[Changes][v0.11.3]


<a name="v0.11.2"></a>
# [v0.11.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.2) - 17 Feb 2024

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


[v0.17.2]: https://github.com/gdsfactory/kfactory/compare/v0.17.1...v0.17.2
[v0.17.1]: https://github.com/gdsfactory/kfactory/compare/v0.17.0...v0.17.1
[v0.17.0]: https://github.com/gdsfactory/kfactory/compare/v0.16.1...v0.17.0
[v0.16.1]: https://github.com/gdsfactory/kfactory/compare/v0.16.0...v0.16.1
[v0.16.0]: https://github.com/gdsfactory/kfactory/compare/v0.15.2...v0.16.0
[v0.15.2]: https://github.com/gdsfactory/kfactory/compare/v0.15.1...v0.15.2
[v0.15.1]: https://github.com/gdsfactory/kfactory/compare/v0.15.0...v0.15.1
[v0.15.0]: https://github.com/gdsfactory/kfactory/compare/v0.14.0...v0.15.0
[v0.14.0]: https://github.com/gdsfactory/kfactory/compare/v0.13.3...v0.14.0
[v0.13.3]: https://github.com/gdsfactory/kfactory/compare/v0.13.2...v0.13.3
[v0.13.2]: https://github.com/gdsfactory/kfactory/compare/v0.13.1...v0.13.2
[v0.13.1]: https://github.com/gdsfactory/kfactory/compare/v0.13.0...v0.13.1
[v0.13.0]: https://github.com/gdsfactory/kfactory/compare/v0.12.3...v0.13.0
[v0.12.3]: https://github.com/gdsfactory/kfactory/compare/v0.12.2...v0.12.3
[v0.12.2]: https://github.com/gdsfactory/kfactory/compare/v0.12.0...v0.12.2
[v0.12.0]: https://github.com/gdsfactory/kfactory/compare/v0.11.4...v0.12.0
[v0.11.4]: https://github.com/gdsfactory/kfactory/compare/v0.11.3...v0.11.4
[v0.11.3]: https://github.com/gdsfactory/kfactory/compare/v0.11.2...v0.11.3
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
