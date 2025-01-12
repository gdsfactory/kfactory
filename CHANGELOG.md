<a id="v0.23.1"></a>
# [v0.23.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.23.1) - 2025-01-05

# What's Changed

## New

- Add BaseKCell to __init__.py [#545](https://github.com/gdsfactory/kfactory/pull/545)

## Bug Fixes

- fix VInstance.bbox and duplication of VKCell [#547](https://github.com/gdsfactory/kfactory/pull/547)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.23.0...v0.23.1


[Changes][v0.23.1]


<a id="v0.23.0"></a>
# [v0.23.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.23.0) - 2025-01-05

# What's Changed

## Breaking

- (d)mirror as tuples instead of points [#544](https://github.com/gdsfactory/kfactory/pull/544)
- Port (d)center as tuple [#541](https://github.com/gdsfactory/kfactory/pull/541)
- Add BaseKCell class and update VKCell and KCell to inherit from it [#528](https://github.com/gdsfactory/kfactory/pull/528)

## New

- (d)mirror as tuples instead of points [#544](https://github.com/gdsfactory/kfactory/pull/544)
- Port (d)center as tuple [#541](https://github.com/gdsfactory/kfactory/pull/541)
- Add BaseKCell class and update VKCell and KCell to inherit from it [#528](https://github.com/gdsfactory/kfactory/pull/528)
- better LockedError message [#536](https://github.com/gdsfactory/kfactory/pull/536)

## Bug Fixes

- Port (d)center as tuple [#541](https://github.com/gdsfactory/kfactory/pull/541)

## Dependency Updates

- Add lockfile and more commands to makefile [#538](https://github.com/gdsfactory/kfactory/pull/538)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.22.0...v0.23.0


[Changes][v0.23.0]


<a id="v0.22.0"></a>
# [v0.22.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.22.0) - 2024-12-19

# What's Changed

## New

- add better handling of placing errors [#532](https://github.com/gdsfactory/kfactory/pull/532)

## Bug Fixes

- fix dict serialization [#531](https://github.com/gdsfactory/kfactory/pull/531)
- Fix ports setter for VKCell [#529](https://github.com/gdsfactory/kfactory/pull/529)
- fix writer using gdsii always [#526](https://github.com/gdsfactory/kfactory/pull/526)
- Fix fill_tiled segfault [#521](https://github.com/gdsfactory/kfactory/pull/521)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.11...v0.22.0


[Changes][v0.22.0]


<a id="v0.21.11"></a>
# [v0.21.11](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.11) - 2024-11-19

# What's Changed

## Bug Fixes

- Remove  loguru catch [#520](https://github.com/gdsfactory/kfactory/pull/520)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.10...v0.21.11


[Changes][v0.21.11]


<a id="v0.21.10"></a>
# [v0.21.10](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.10) - 2024-11-19

# What's Changed

## Bug Fixes

- clean the name in kf show [#519](https://github.com/gdsfactory/kfactory/pull/519)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.8...v0.21.10


[Changes][v0.21.10]


<a id="v0.21.8"></a>
# [v0.21.8](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.8) - 2024-11-18

# What's Changed

## New

- Add Instance.purpose [#514](https://github.com/gdsfactory/kfactory/pull/514)

## Bug Fixes

- at least partially fix the fill_tiled error [#518](https://github.com/gdsfactory/kfactory/pull/518)
- fix: MetaData type alias and __all__ exports [#516](https://github.com/gdsfactory/kfactory/pull/516)
- fix str(Port) [#512](https://github.com/gdsfactory/kfactory/pull/512)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.7...v0.21.8


[Changes][v0.21.8]


<a id="v0.21.7"></a>
# [v0.21.7](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.7) - 2024-11-06

# What's Changed

## Bug Fixes

- fix cli arg [#508](https://github.com/gdsfactory/kfactory/pull/508)
- fix convert to static not taking all metainfo [#507](https://github.com/gdsfactory/kfactory/pull/507)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.6...v0.21.7


[Changes][v0.21.7]


<a id="v0.21.6"></a>
# [v0.21.6](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.6) - 2024-10-29

# What's Changed

## New

- add suffix [#504](https://github.com/gdsfactory/kfactory/pull/504)

## Bug Fixes

- fix error in width calculation of waypoints [#505](https://github.com/gdsfactory/kfactory/pull/505)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.5...v0.21.6


[Changes][v0.21.6]


<a id="v0.21.5"></a>
# [v0.21.5](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.5) - 2024-10-21

# What's Changed

## New

- make add_ports agnostic to kcl [#501](https://github.com/gdsfactory/kfactory/pull/501)
- add length and length_straight to electrical routes [#502](https://github.com/gdsfactory/kfactory/pull/502)

## Bug Fixes

- fix missing arg [#503](https://github.com/gdsfactory/kfactory/pull/503)
- fix typo [#499](https://github.com/gdsfactory/kfactory/pull/499)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.4...v0.21.5


[Changes][v0.21.5]


<a id="v0.21.4"></a>
# [v0.21.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.4) - 2024-10-17

# What's Changed

## New

- add port reorientation for route_bundle [#498](https://github.com/gdsfactory/kfactory/pull/498)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.3...v0.21.4


[Changes][v0.21.4]


<a id="v0.21.3"></a>
# [v0.21.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.3) - 2024-10-17

# What's Changed

## New

- add saveoptions to build cli [#497](https://github.com/gdsfactory/kfactory/pull/497)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.2...v0.21.3


[Changes][v0.21.3]


<a id="v0.21.2"></a>
# [v0.21.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.2) - 2024-10-17

# What's Changed

## New

- add tag support for cell decorator [#496](https://github.com/gdsfactory/kfactory/pull/496)
- Add Router start/end straight steps [#493](https://github.com/gdsfactory/kfactory/pull/493)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.1...v0.21.2


[Changes][v0.21.2]


<a id="v0.21.1"></a>
# [v0.21.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.1) - 2024-10-17

# What's Changed

## New

- add transform_ports option to KCell.transform [#495](https://github.com/gdsfactory/kfactory/pull/495)
- add instance iterator which returns coord plus port [#491](https://github.com/gdsfactory/kfactory/pull/491)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.21.0...v0.21.1


[Changes][v0.21.1]


<a id="v0.21.0"></a>
# [v0.21.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.21.0) - 2024-10-10

# What's Changed

## New

- Add SymmetricalCrossSection [#481](https://github.com/gdsfactory/kfactory/pull/481)

## Bug Fixes

- fix layerenum [#490](https://github.com/gdsfactory/kfactory/pull/490)
- fix naming of cells from vinsts [#489](https://github.com/gdsfactory/kfactory/pull/489)
- fix route_bundle bbox ignore for single route (or matching opposite side) [#488](https://github.com/gdsfactory/kfactory/pull/488)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.8...v0.21.0


[Changes][v0.21.0]


<a id="v0.20.8"></a>
# [v0.20.8](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.8) - 2024-10-02

# What's Changed

## Bug Fixes

- fix AREF __getitem__ for instance ports and generic route_bundle [#484](https://github.com/gdsfactory/kfactory/pull/484)
- fix AREF ports [#483](https://github.com/gdsfactory/kfactory/pull/483)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.7...v0.20.8


[Changes][v0.20.8]


<a id="v0.20.7"></a>
# [v0.20.7](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.7) - 2024-09-29

# What's Changed

## Bug Fixes

- decrease log level of layout_cache and klayout version mismatch log messages [#480](https://github.com/gdsfactory/kfactory/pull/480)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.6...v0.20.7


[Changes][v0.20.7]


<a id="v0.20.6"></a>
# [v0.20.6](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.6) - 2024-09-27

# What's Changed

## New

- add waypoint routing [#473](https://github.com/gdsfactory/kfactory/pull/473)

## Bug Fixes

- re-add LayerEnum to be available as kf.LayerEnum [#476](https://github.com/gdsfactory/kfactory/pull/476)

## Dependency Updates

- bump klayout to 0.29.7 [#478](https://github.com/gdsfactory/kfactory/pull/478)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.5...v0.20.6


[Changes][v0.20.6]


<a id="v0.20.5"></a>
# [v0.20.5](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.5) - 2024-09-13

# What's Changed

## New

- Better build cli [#471](https://github.com/gdsfactory/kfactory/pull/471)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.4...v0.20.5


[Changes][v0.20.5]


<a id="v0.20.4"></a>
# [v0.20.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.4) - 2024-09-12

# What's Changed

## Bug Fixes

- fix layout-cache not honoring overwrite-existing [#470](https://github.com/gdsfactory/kfactory/pull/470)
- fix apply_bbox for LayerInfo objects [#469](https://github.com/gdsfactory/kfactory/pull/469)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.3...v0.20.4


[Changes][v0.20.4]


<a id="v0.20.3"></a>
# [v0.20.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.3) - 2024-09-06

# What's Changed

## Bug Fixes

- fix add_port using arg call instead of kwarg call [#466](https://github.com/gdsfactory/kfactory/pull/466)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.2...v0.20.3


[Changes][v0.20.3]


<a id="v0.20.2"></a>
# [v0.20.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.2) - 2024-09-05

# What's Changed

## Bug Fixes

- Fix meta [#465](https://github.com/gdsfactory/kfactory/pull/465)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.1...v0.20.2


[Changes][v0.20.2]


<a id="v0.20.1"></a>
# [v0.20.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.1) - 2024-09-01

# What's Changed

## New

- add config option for custom show functions  [#461](https://github.com/gdsfactory/kfactory/pull/461)

## Bug Fixes

- fix generic route not passing routing width to placer_function [#463](https://github.com/gdsfactory/kfactory/pull/463)
- fix errors for `kf run` not finding modules. Change syntax [#462](https://github.com/gdsfactory/kfactory/pull/462)

## Documentation

- add config option for custom show functions  [#461](https://github.com/gdsfactory/kfactory/pull/461)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.20.0...v0.20.1


[Changes][v0.20.1]


<a id="v0.20.0"></a>
# [v0.20.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.20.0) - 2024-08-29

# What's Changed

## New

- clean up route_bundle and add a generic version [#456](https://github.com/gdsfactory/kfactory/pull/456)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.19.2...v0.20.0


[Changes][v0.20.0]


<a id="v0.19.2"></a>
# [v0.19.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.19.2) - 2024-08-29

# What's Changed

## Bug Fixes

- fix errors in enclosures and relax some port layer constraints [#460](https://github.com/gdsfactory/kfactory/pull/460)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.19.1...v0.19.2


[Changes][v0.19.2]


<a id="v0.19.1"></a>
# [v0.19.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.19.1) - 2024-08-26

# What's Changed

## Bug Fixes

- relax  to  in Port and Ports when finding layers [#459](https://github.com/gdsfactory/kfactory/pull/459)
- fix [#452](https://github.com/gdsfactory/kfactory/issues/452) [#454](https://github.com/gdsfactory/kfactory/pull/454)
- fix load_layout_options [#453](https://github.com/gdsfactory/kfactory/pull/453)

## Other changes

- Fixed another `oror` output [#455](https://github.com/gdsfactory/kfactory/pull/455)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.19.0...v0.19.1


[Changes][v0.19.1]


<a id="v0.19.0"></a>
# [v0.19.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.19.0) - 2024-08-14

# What's Changed

## Breaking

- Improve layers so that they can be passed easily by LayerInfo and not only by index [#439](https://github.com/gdsfactory/kfactory/pull/439)

## New

- Improve layers so that they can be passed easily by LayerInfo and not only by index [#439](https://github.com/gdsfactory/kfactory/pull/439)

## Bug Fixes

- better instance default name using trans instead of .x [#450](https://github.com/gdsfactory/kfactory/pull/450)
- fix write_context_info [#448](https://github.com/gdsfactory/kfactory/pull/448)
- Add missing space in KLayout version warning [#447](https://github.com/gdsfactory/kfactory/pull/447)
- ensure cell decorated functions return component [#443](https://github.com/gdsfactory/kfactory/pull/443)
- fix c.flatten(merge=True) deleting texts [#441](https://github.com/gdsfactory/kfactory/pull/441)
- Adjust AttributeError text in optical routing for taper and bend [#438](https://github.com/gdsfactory/kfactory/pull/438)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.18.4...v0.19.0


[Changes][v0.19.0]


<a id="v0.18.4"></a>
# [v0.18.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.18.4) - 2024-07-23

# What's Changed

## Bug Fixes

- fix the other case of model_dump [#436](https://github.com/gdsfactory/kfactory/pull/436)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.18.3...v0.18.4


[Changes][v0.18.4]


<a id="v0.18.3"></a>
# [v0.18.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.18.3) - 2024-07-23

## What's Changed
* fix _port by [@joamatab](https://github.com/joamatab) in [#435](https://github.com/gdsfactory/kfactory/pull/435)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.18.2...v0.18.3

[Changes][v0.18.3]


<a id="v0.18.2"></a>
# [v0.18.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.18.2) - 2024-07-23

# What's Changed

## New

- add packing functions for Instances and KCells [#431](https://github.com/gdsfactory/kfactory/pull/431)
- Add InstanceGroup [#430](https://github.com/gdsfactory/kfactory/pull/430)

## Bug Fixes

- fix _port [#435](https://github.com/gdsfactory/kfactory/pull/435)
- fix add_ports in case port.kcl is not ports.kcl [#434](https://github.com/gdsfactory/kfactory/pull/434)
- fix error message [#432](https://github.com/gdsfactory/kfactory/pull/432)

## Other changes

- Fixed double `or` print statement [#428](https://github.com/gdsfactory/kfactory/pull/428)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.18.1...v0.18.2


[Changes][v0.18.2]


<a id="v0.18.1"></a>
# [v0.18.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.18.1) - 2024-07-17

# What's Changed

## Bug Fixes

- Fix `KCLayout.read(..., register_cells=True)` [#426](https://github.com/gdsfactory/kfactory/pull/426)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.18.0...v0.18.1


[Changes][v0.18.1]


<a id="v0.18.0"></a>
# [v0.18.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.18.0) - 2024-07-16

# What's Changed

## New

- Add name debugging config [#421](https://github.com/gdsfactory/kfactory/pull/421)
- make OpticalManhattanRoute better [#418](https://github.com/gdsfactory/kfactory/pull/418)

## Bug Fixes

- find dotenv [#415](https://github.com/gdsfactory/kfactory/pull/415)

## Dependency Updates

- update klayout and pre-commit [#419](https://github.com/gdsfactory/kfactory/pull/419)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.8...v0.18.0


[Changes][v0.18.0]


<a id="v0.17.8"></a>
# [v0.17.8](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.8) - 2024-06-27

# What's Changed

## Bug Fixes

- fix kclayout nested cells and ports/metainfo issues [#414](https://github.com/gdsfactory/kfactory/pull/414)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.7...v0.17.8


[Changes][v0.17.8]


<a id="v0.17.7"></a>
# [v0.17.7](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.7) - 2024-06-27

# What's Changed

## New

- Add check for klayout/klive version vs kfactory [#411](https://github.com/gdsfactory/kfactory/pull/411)

## Bug Fixes

- fix hierarchy of yaml parser and add test [#413](https://github.com/gdsfactory/kfactory/pull/413)
- fix l2n extraction and add test [#412](https://github.com/gdsfactory/kfactory/pull/412)

## Documentation

- fix l2n extraction and add test [#412](https://github.com/gdsfactory/kfactory/pull/412)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.6...v0.17.7


[Changes][v0.17.7]


<a id="v0.17.6"></a>
# [v0.17.6](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.6) - 2024-06-27

# What's Changed

## New

- Use tempfile if called from IPython [#405](https://github.com/gdsfactory/kfactory/pull/405)
- Routing indirect fixes [#409](https://github.com/gdsfactory/kfactory/pull/409)

## Bug Fixes

- fix connection issue caring about mirror when it should not [#403](https://github.com/gdsfactory/kfactory/pull/403)
- fix indirect routing [#402](https://github.com/gdsfactory/kfactory/pull/402)

## Documentation

- Routing indirect fixes [#409](https://github.com/gdsfactory/kfactory/pull/409)
- fix connection issue caring about mirror when it should not [#403](https://github.com/gdsfactory/kfactory/pull/403)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.5...v0.17.6


[Changes][v0.17.6]


<a id="v0.17.5"></a>
# [v0.17.5](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.5) - 2024-06-16

# What's Changed

## New

- add display_kcell display_type [#396](https://github.com/gdsfactory/kfactory/pull/396)

## Bug Fixes

- works with partials [#399](https://github.com/gdsfactory/kfactory/pull/399)
- full test suite for smart routing and error fixes [#398](https://github.com/gdsfactory/kfactory/pull/398)
- fix basename usage in cell decorator [#400](https://github.com/gdsfactory/kfactory/pull/400)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.4...v0.17.5


[Changes][v0.17.5]


<a id="v0.17.4"></a>
# [v0.17.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.4) - 2024-06-12

# What's Changed

## New

- add __contains__ to settings/units/info [#395](https://github.com/gdsfactory/kfactory/pull/395)

## Bug Fixes

- fix routing errors and add a better test [#397](https://github.com/gdsfactory/kfactory/pull/397)
- fix connect when using port objects on self [#393](https://github.com/gdsfactory/kfactory/pull/393)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.3...v0.17.4


[Changes][v0.17.4]


<a id="v0.17.3"></a>
# [v0.17.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.3) - 2024-06-10

# What's Changed

## Bug Fixes

- fix erroneous start for route_loosely [#390](https://github.com/gdsfactory/kfactory/pull/390)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.2...v0.17.3


[Changes][v0.17.3]


<a id="v0.17.2"></a>
# [v0.17.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.2) - 2024-06-10

# What's Changed

## New

- Add functional `check_ports` to `@cell` decorators [#389](https://github.com/gdsfactory/kfactory/pull/389)

## Bug Fixes

- fix routing issues with bounding boxes [#388](https://github.com/gdsfactory/kfactory/pull/388)
- fix cases in bundle routing [#387](https://github.com/gdsfactory/kfactory/pull/387)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.17.1...v0.17.2


[Changes][v0.17.2]


<a id="v0.17.1"></a>
# [v0.17.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.1) - 2024-06-08

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


<a id="v0.17.0"></a>
# [v0.17.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.17.0) - 2024-06-05

# What's Changed

## Breaking

- Drop rec_dicts flag and make it default to use rec dict inspection [#375](https://github.com/gdsfactory/kfactory/pull/375)

## Bug Fixes

- Improve and fix enclosure_tiled for KCellEnclosure and LayerEnclosure [#374](https://github.com/gdsfactory/kfactory/pull/374)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.16.1...v0.17.0


[Changes][v0.17.0]


<a id="v0.16.1"></a>
# [v0.16.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.16.1) - 2024-06-02

# What's Changed

## New

- Improve logger [#368](https://github.com/gdsfactory/kfactory/pull/368)

## Bug Fixes

- fix locked cell error [#367](https://github.com/gdsfactory/kfactory/pull/367)

## Documentation

- Improve logger [#368](https://github.com/gdsfactory/kfactory/pull/368)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.16.0...v0.16.1


[Changes][v0.16.1]


<a id="v0.16.0"></a>
# [v0.16.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.16.0) - 2024-06-02

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


<a id="v0.15.2"></a>
# [v0.15.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.2) - 2024-05-29

# What's Changed

## Bug Fixes

- fix global config settings only being set on first import [#345](https://github.com/gdsfactory/kfactory/pull/345)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.15.1...v0.15.2


[Changes][v0.15.2]


<a id="v0.15.1"></a>
# [v0.15.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.1) - 2024-05-29

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


<a id="v0.15.0"></a>
# [v0.15.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.15.0) - 2024-05-27

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


<a id="v0.14.0"></a>
# [v0.14.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.14.0) - 2024-05-24

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


<a id="v0.13.3"></a>
# [v0.13.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.3) - 2024-05-21

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


<a id="v0.13.2"></a>
# [v0.13.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.2) - 2024-05-15

# What's Changed

## New

- Improve fill tiled with row/column vectors [#314](https://github.com/gdsfactory/kfactory/pull/314)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.1...v0.13.2

[Changes][v0.13.2]


<a id="v0.13.1"></a>
# [v0.13.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.1) - 2024-05-15

# What's Changed

## Bug Fixes

- fix grid instance array not properly setting up the array [#310](https://github.com/gdsfactory/kfactory/pull/310)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.13.0...v0.13.1


[Changes][v0.13.1]


<a id="v0.13.0"></a>
# [v0.13.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.13.0) - 2024-05-07

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


<a id="v0.12.3"></a>
# [v0.12.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.3) - 2024-03-06

# What's Changed

## Bug Fixes

- Fix KCellEnclosure and rename bbox_per_layer to bbox [#270](https://github.com/gdsfactory/kfactory/pull/270)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.12.2...v0.12.3


[Changes][v0.12.3]


<a id="v0.12.2"></a>
# [v0.12.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.2) - 2024-03-06

# What's Changed

## Bug Fixes

- Fix initialization of KCLayout.constants [#269](https://github.com/gdsfactory/kfactory/pull/269)
- Fix factories for euler and taper [#268](https://github.com/gdsfactory/kfactory/pull/268)
- fix KCLayout not allowing constants in the constructor [#267](https://github.com/gdsfactory/kfactory/pull/267)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.12.0...v0.12.2


[Changes][v0.12.2]


<a id="v0.12.0"></a>
# [v0.12.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.12.0) - 2024-03-01

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


<a id="v0.11.4"></a>
# [v0.11.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.4) - 2024-02-28

# What's Changed

## New

- Add automatic registering of KCell-functions to the KCLayout.factories [#261](https://github.com/gdsfactory/kfactory/pull/261)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.3...v0.11.4


[Changes][v0.11.4]


<a id="v0.11.3"></a>
# [v0.11.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.3) - 2024-02-27

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


<a id="v0.11.2"></a>
# [v0.11.2](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.2) - 2024-02-17

# What's Changed

## New

- Add top_kcell(s) functions and fix Instance creation [#251](https://github.com/gdsfactory/kfactory/pull/251)
- Allow inheritance from standard cells [#249](https://github.com/gdsfactory/kfactory/pull/249)
- Improve minkowski algorithms for violation fixing [#248](https://github.com/gdsfactory/kfactory/pull/248)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.1...v0.11.2


[Changes][v0.11.2]


<a id="v0.11.1"></a>
# [v0.11.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.1) - 2024-02-08

# What's Changed

## Bug Fixes

- Fix Layout read trying to update ports on locked cells [#244](https://github.com/gdsfactory/kfactory/pull/244)

## Dependency Updates

- Update ruff and lsp configs [#243](https://github.com/gdsfactory/kfactory/pull/243)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.11.0...v0.11.1


[Changes][v0.11.1]


<a id="v0.11.0"></a>
# [v0.11.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.11.0) - 2024-02-02

# What's Changed

## New

- Multi PDK [#241](https://github.com/gdsfactory/kfactory/pull/241)

## Other changes

- Version numbers [#242](https://github.com/gdsfactory/kfactory/pull/242)

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.10.3...v0.11.0


[Changes][v0.11.0]


<a id="v0.10.3"></a>
# [v0.10.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.3) - 2024-01-12

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


<a id="v0.10.2"></a>
# [0.10.2 - 2023-12-08 (v0.10.2)](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.2) - 2023-12-08

### Fixed

- Fix no_warn being ignored in transform 

[Changes][v0.10.2]


<a id="v0.10.1"></a>
# [0.10.1 - 2023-12-05 (v0.10.1)](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.1) - 2023-12-05

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


<a id="v0.10.0"></a>
# [v0.10.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.10.0) - 2024-06-16

## What's Changed
* add Instance setter and getter for center by [@joamatab](https://github.com/joamatab) in [#191](https://github.com/gdsfactory/kfactory/pull/191)
* Add port center setter getter by [@joamatab](https://github.com/joamatab) in [#192](https://github.com/gdsfactory/kfactory/pull/192)
* improve instance setters by [@joamatab](https://github.com/joamatab) in [#193](https://github.com/gdsfactory/kfactory/pull/193)
* rename autorename_ports to auto_rename_ports by [@joamatab](https://github.com/joamatab) in [#195](https://github.com/gdsfactory/kfactory/pull/195)
* rename port position to center by [@joamatab](https://github.com/joamatab) in [#199](https://github.com/gdsfactory/kfactory/pull/199)
* Make Instance.flatten(<int|None>) work correctly with KCell/Instance by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#202](https://github.com/gdsfactory/kfactory/pull/202)
* add kf.KCell.center property by [@joamatab](https://github.com/joamatab) in [#200](https://github.com/gdsfactory/kfactory/pull/200)
* add Instance.mirror and Instance.d.mirror by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#204](https://github.com/gdsfactory/kfactory/pull/204)
* add towncrier news by [@joamatab](https://github.com/joamatab) in [#205](https://github.com/gdsfactory/kfactory/pull/205)
* route optical uses allow_small_routes by [@joamatab](https://github.com/joamatab) in [#209](https://github.com/gdsfactory/kfactory/pull/209)
* add ports length by [@joamatab](https://github.com/joamatab) in [#210](https://github.com/gdsfactory/kfactory/pull/210)
* (Basic) Bundle routing by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#212](https://github.com/gdsfactory/kfactory/pull/212)
* Fixed typo `enclosure_mape` -> `enclosure_map` by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#213](https://github.com/gdsfactory/kfactory/pull/213)
* remove debug prints by [@joamatab](https://github.com/joamatab) in [#214](https://github.com/gdsfactory/kfactory/pull/214)
* use image by default by [@joamatab](https://github.com/joamatab) in [#215](https://github.com/gdsfactory/kfactory/pull/215)
* add invert to droute_manhattan by [@joamatab](https://github.com/joamatab) in [#217](https://github.com/gdsfactory/kfactory/pull/217)
* better_odd_port_width_message by [@joamatab](https://github.com/joamatab) in [#220](https://github.com/gdsfactory/kfactory/pull/220)
* Added `rec_dict` to `@cell` decorator to allow for recursive dictionaries by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#221](https://github.com/gdsfactory/kfactory/pull/221)
* more consistent names for routes by [@joamatab](https://github.com/joamatab) in [#226](https://github.com/gdsfactory/kfactory/pull/226)
* Virtual Cells by [@sebastian-goeldi](https://github.com/sebastian-goeldi) in [#228](https://github.com/gdsfactory/kfactory/pull/228)


**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.9.3...v0.10.0

[Changes][v0.10.0]


<a id="v0.9.3"></a>
# [v0.9.3](https://github.com/gdsfactory/kfactory/releases/tag/v0.9.3) - 2024-06-16

**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.9.2...v0.9.3

[Changes][v0.9.3]


<a id="v0.9.1"></a>
# [v0.9.1](https://github.com/gdsfactory/kfactory/releases/tag/v0.9.1) - 2024-06-16

## What's Changed
* Bump actions/checkout from 3 to 4 by [@dependabot](https://github.com/dependabot) in [#186](https://github.com/gdsfactory/kfactory/pull/186)
* get_cells by [@joamatab](https://github.com/joamatab) in [#187](https://github.com/gdsfactory/kfactory/pull/187)


**Full Changelog**: https://github.com/gdsfactory/kfactory/compare/v0.9.0...v0.9.1

[Changes][v0.9.1]


<a id="v0.9.0"></a>
# [v0.9.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.9.0) - 2023-09-25

### Added

- Added  to be set by  decorator [#180](https://github.com/gdsfactory/kfactory/issues/180)
- Added __contains__ to port and __eq__ [#182](https://github.com/gdsfactory/kfactory/issues/182)
- Add PDK capabilities to KCLayout [#171](https://github.com/gdsfactory/kfactory/pull/171) 
- Added KCell.connectivity_chek to check for port alignments and overlaps 
- Added a cli based on [typer](https://typer.tiangolo.com) to allow running of functions (taking int/float/str args) and allow upload/update of gdatasea edafiles 


### Fixed

- Fixed throw a critical log message on negative width and angles and convert them to positive ones [#183](https://github.com/gdsfactory/kfactory/issues/183)


[Changes][v0.9.0]


<a id="v0.8.0"></a>
# [v0.8.0](https://github.com/gdsfactory/kfactory/releases/tag/v0.8.0) - 2023-06-14

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


<a id="v0.7.5"></a>
# [v0.7.5](https://github.com/gdsfactory/kfactory/releases/tag/v0.7.5) - 2023-06-01

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


<a id="v0.7.4"></a>
# [v0.7.4](https://github.com/gdsfactory/kfactory/releases/tag/v0.7.4) - 2023-05-29

## [0.7.4](https://github.com/gdsfactory/klive/tree/0.7.4) - 2023-05-29


### Added

- add tbump and towncrier for changelog and bumping [#129](https://github.com/gdsfactory/klive/issues/129)


### Fixed

- enable non manhattan bend ports, and document how to get rid of gaps [#131](https://github.com/gdsfactory/klive/issues/131)


[Changes][v0.7.4]


<a id="v0.6.0"></a>
# [0.6.0 (v0.6.0)](https://github.com/gdsfactory/kfactory/releases/tag/v0.6.0) - 2023-04-18

# kcell.py
* KCell and Instance don´t  inherit from `kdb.Cell` / `kdb.Instance` anymore. They should still transparently proxy to them
* Ports automatically convert um <-> dbu
  * no more DPort/DCplxPort/ICplxPort

[Changes][v0.6.0]


<a id="v0.4.1"></a>
# [Fix (Cplx)KCell.dup (v0.4.1)](https://github.com/gdsfactory/kfactory/releases/tag/v0.4.1) - 2023-02-24

* `KCell` and `CplxKCell` are now properly copying their instances when copied using `dup` [KLayout/klayout#1300](https://github.com/KLayout/klayout/issues/1300)

[Changes][v0.4.1]


<a id="v0.4.0"></a>
# [Complex Cells (v0.4.0)](https://github.com/gdsfactory/kfactory/releases/tag/v0.4.0) - 2023-02-21

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


[v0.23.1]: https://github.com/gdsfactory/kfactory/compare/v0.23.0...v0.23.1
[v0.23.0]: https://github.com/gdsfactory/kfactory/compare/v0.22.0...v0.23.0
[v0.22.0]: https://github.com/gdsfactory/kfactory/compare/v0.21.11...v0.22.0
[v0.21.11]: https://github.com/gdsfactory/kfactory/compare/v0.21.10...v0.21.11
[v0.21.10]: https://github.com/gdsfactory/kfactory/compare/v0.21.8...v0.21.10
[v0.21.8]: https://github.com/gdsfactory/kfactory/compare/v0.21.7...v0.21.8
[v0.21.7]: https://github.com/gdsfactory/kfactory/compare/v0.21.6...v0.21.7
[v0.21.6]: https://github.com/gdsfactory/kfactory/compare/v0.21.5...v0.21.6
[v0.21.5]: https://github.com/gdsfactory/kfactory/compare/v0.21.4...v0.21.5
[v0.21.4]: https://github.com/gdsfactory/kfactory/compare/v0.21.3...v0.21.4
[v0.21.3]: https://github.com/gdsfactory/kfactory/compare/v0.21.2...v0.21.3
[v0.21.2]: https://github.com/gdsfactory/kfactory/compare/v0.21.1...v0.21.2
[v0.21.1]: https://github.com/gdsfactory/kfactory/compare/v0.21.0...v0.21.1
[v0.21.0]: https://github.com/gdsfactory/kfactory/compare/v0.20.8...v0.21.0
[v0.20.8]: https://github.com/gdsfactory/kfactory/compare/v0.20.7...v0.20.8
[v0.20.7]: https://github.com/gdsfactory/kfactory/compare/v0.20.6...v0.20.7
[v0.20.6]: https://github.com/gdsfactory/kfactory/compare/v0.20.5...v0.20.6
[v0.20.5]: https://github.com/gdsfactory/kfactory/compare/v0.20.4...v0.20.5
[v0.20.4]: https://github.com/gdsfactory/kfactory/compare/v0.20.3...v0.20.4
[v0.20.3]: https://github.com/gdsfactory/kfactory/compare/v0.20.2...v0.20.3
[v0.20.2]: https://github.com/gdsfactory/kfactory/compare/v0.20.1...v0.20.2
[v0.20.1]: https://github.com/gdsfactory/kfactory/compare/v0.20.0...v0.20.1
[v0.20.0]: https://github.com/gdsfactory/kfactory/compare/v0.19.2...v0.20.0
[v0.19.2]: https://github.com/gdsfactory/kfactory/compare/v0.19.1...v0.19.2
[v0.19.1]: https://github.com/gdsfactory/kfactory/compare/v0.19.0...v0.19.1
[v0.19.0]: https://github.com/gdsfactory/kfactory/compare/v0.18.4...v0.19.0
[v0.18.4]: https://github.com/gdsfactory/kfactory/compare/v0.18.3...v0.18.4
[v0.18.3]: https://github.com/gdsfactory/kfactory/compare/v0.18.2...v0.18.3
[v0.18.2]: https://github.com/gdsfactory/kfactory/compare/v0.18.1...v0.18.2
[v0.18.1]: https://github.com/gdsfactory/kfactory/compare/v0.18.0...v0.18.1
[v0.18.0]: https://github.com/gdsfactory/kfactory/compare/v0.17.8...v0.18.0
[v0.17.8]: https://github.com/gdsfactory/kfactory/compare/v0.17.7...v0.17.8
[v0.17.7]: https://github.com/gdsfactory/kfactory/compare/v0.17.6...v0.17.7
[v0.17.6]: https://github.com/gdsfactory/kfactory/compare/v0.17.5...v0.17.6
[v0.17.5]: https://github.com/gdsfactory/kfactory/compare/v0.17.4...v0.17.5
[v0.17.4]: https://github.com/gdsfactory/kfactory/compare/v0.17.3...v0.17.4
[v0.17.3]: https://github.com/gdsfactory/kfactory/compare/v0.17.2...v0.17.3
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
[v0.10.1]: https://github.com/gdsfactory/kfactory/compare/v0.10.0...v0.10.1
[v0.10.0]: https://github.com/gdsfactory/kfactory/compare/v0.9.3...v0.10.0
[v0.9.3]: https://github.com/gdsfactory/kfactory/compare/v0.9.1...v0.9.3
[v0.9.1]: https://github.com/gdsfactory/kfactory/compare/v0.9.0...v0.9.1
[v0.9.0]: https://github.com/gdsfactory/kfactory/compare/v0.8.0...v0.9.0
[v0.8.0]: https://github.com/gdsfactory/kfactory/compare/v0.7.5...v0.8.0
[v0.7.5]: https://github.com/gdsfactory/kfactory/compare/v0.7.4...v0.7.5
[v0.7.4]: https://github.com/gdsfactory/kfactory/compare/v0.6.0...v0.7.4
[v0.6.0]: https://github.com/gdsfactory/kfactory/compare/v0.4.1...v0.6.0
[v0.4.1]: https://github.com/gdsfactory/kfactory/compare/v0.4.0...v0.4.1
[v0.4.0]: https://github.com/gdsfactory/kfactory/tree/v0.4.0

<!-- Generated by https://github.com/rhysd/changelog-from-release v3.8.1 -->
