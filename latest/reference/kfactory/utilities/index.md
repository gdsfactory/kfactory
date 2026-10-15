# utilities

## as\_png\_data

```
as_png_data(c: ProtoTKCell[Any], layer_properties: str | Path | None = None, resolution: tuple[int, int] = (800, 600), synchronous: bool = True, markers: list[tuple[DShapeLike, MarkerConfig]] | None = None) -> bytes
```

Render a cell to PNG bytes via a headless `lay.LayoutView`.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `ProtoTKCell[Any]` | cell to render. | *required* |
| `layer_properties` | `str \| Path \| None` | optional `.lyp` to apply. | `None` |
| `resolution` | `tuple[int, int]` | `(width, height)` in pixels. | `(800, 600)` |
| `synchronous` | `bool` | `True` to render synchronously (default), `False` to return whatever the view currently has. | `True` |
| `markers` | `list[tuple[DShapeLike, MarkerConfig]] \| None` | optional list of `(shape, config)` pairs. Each shape becomes a `lay.Marker` overlay on the view; `config` is the same `MarkerConfig` dict that `kfactory.show` accepts (`color`, `line_width`, `halo`, …). When markers are supplied, the view zooms to the union of all marker bounding boxes expanded by 10 % instead of fitting the full cell. | `None` |

## check\_cell\_ports

```
check_cell_ports(p1: ProtoPort[Any], p2: ProtoPort[Any]) -> int
```

Check if two ports are the same.

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `int` | `int` | A bitwise representation of the differences between the two ports. |

## check\_inst\_ports

```
check_inst_ports(p1: Port, p2: Port) -> int
```

Check if two ports are the same.

Returns:

| Name | Type | Description |
| --- | --- | --- |
| `int` | `int` | A bitwise representation of the differences between the two ports. |

## dpolygon\_from\_array

```
dpolygon_from_array(array: Iterable[tuple[float, float]]) -> kdb.DPolygon
```

Create a DPolygon from a 2D array-like structure. (um version).

Array-like: `[[x1,y1],[x2,y2],...]`

## ensure\_build\_directory

```
ensure_build_directory(subdirectory: str = 'mask', create_gitignore: bool = True) -> Path | None
```

Ensure build directory exists with proper gitignore.

This function consolidates all build directory creation logic, including git repository detection and .gitignore creation.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `subdirectory` | `str` | Subdirectory under build/ (e.g., 'mask', 'session/kcls'). | `'mask'` |
| `create_gitignore` | `bool` | Whether to create .gitignore in build directory. | `True` |

Returns:

| Type | Description |
| --- | --- |
| `Path \| None` | Path to the build subdirectory or None if not in a git repo. |

## get\_build\_path

```
get_build_path(filename: str, subdirectory: str = 'mask', file_format: str = 'gds') -> tuple[Path, bool]
```

Get the appropriate build path for a file.

Determines whether to use a git-tracked build directory or temp directory, and creates necessary directories.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `filename` | `str` | Base filename (without extension). | *required* |
| `subdirectory` | `str` | Subdirectory under build/ (e.g., 'mask', 'gds', 'oas'). | `'mask'` |
| `file_format` | `str` | File extension/format (e.g., 'gds', 'oas', 'lyrdb'). | `'gds'` |

Returns:

<table>       <thead>         <tr>           <th>Type</th>           <th>Description</th>         </tr>       </thead>       <tbody>           <tr class="doc-section-item">             <td>                   <code><autoref backlink-anchor="kfactory.utilities.get_build_path" backlink-type="returned-by" hover="" identifier="pathlib.Path" optional="">Path</autoref></code>             </td>             <td>               <div class="doc-md-description">                 <p>Tuple of (file_path, should_delete):</p>                </div>             </td>           </tr>           <tr class="doc-section-item">             <td>                   <code><autoref backlink-anchor="kfactory.utilities.get_build_path" backlink-type="returned-by" identifier="bool" optional="">bool</autoref></code>             </td>             <td>               <div class="doc-md-description">                 <ul> <li>If in git repo: returns build directory path, False</li> </ul>                </div>             </td>           </tr>           <tr class="doc-section-item">             <td>                   <code><autoref backlink-anchor="kfactory.utilities.get_build_path" backlink-type="returned-by" identifier="tuple" optional="">tuple</autoref>[<autoref backlink-anchor="kfactory.utilities.get_build_path" backlink-type="returned-by" hover="" identifier="pathlib.Path" optional="">Path</autoref>, <autoref backlink-anchor="kfactory.utilities.get_build_path" backlink-type="returned-by" identifier="bool" optional="">bool</autoref>]</code>             </td>             <td>               <div class="doc-md-description">                 <ul> <li>Otherwise: returns temp directory path, True</li> </ul>                </div>             </td>           </tr>       </tbody>     </table>

## get\_session\_directory

```
get_session_directory(custom_dir: Path | None = None) -> Path
```

Get or create session cache directory.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `custom_dir` | `Path \| None` | Optional custom directory override. | `None` |

Returns:

| Type | Description |
| --- | --- |
| `Path` | Path to session/kcls directory. |

## instance\_port\_name

```
instance_port_name(inst: Instance, port: ProtoPort[Any]) -> str
```

Create a name for an instance port.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `inst` | `Instance` | The instance. | *required* |
| `port` | `ProtoPort[Any]` | The port. | *required* |

## load\_layout\_options

```
load_layout_options(**attributes: Any) -> kdb.LoadLayoutOptions
```

Default options for loading GDS/OAS.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `attributes` | `Any` | Set attributes of the layout load option object. E.g. to set the handling of cell name conflicts pass `cell_conflict_resolution=kdb.LoadLayoutOptions.CellConflictResolution.OverwriteCell`. | `{}` |

## polygon\_from\_array

```
polygon_from_array(array: Iterable[tuple[int, int]]) -> kdb.Polygon
```

Create a DPolygon from a 2D array-like structure. (dbu version).

Array-like: `[[x1,y1],[x2,y2],...]`

## pprint\_pins

```
pprint_pins(pins: Iterable[Pin] | Iterable[DPin], unit: Literal['dbu', 'um'] | None = None) -> Table
```

Print ports as a table.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `pins` | `Iterable[Pin] \| Iterable[DPin]` | The pins which should be printed. | *required* |
| `unit` | `Literal['dbu', 'um'] \| None` | Define the print type of the ports. If None, any port which can be represented accurately by a dbu representation will be printed in dbu otherwise in um. 'dbu'/'um' will force the printing to enforce one or the other representation | `None` |

## pprint\_ports

```
pprint_ports(ports: Iterable[ProtoPort[Any]], unit: Literal['dbu', 'um'] | None = None) -> Table
```

Print ports as a table.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Iterable[ProtoPort[Any]]` | The ports which should be printed. | *required* |
| `unit` | `Literal['dbu', 'um'] \| None` | Define the print type of the ports. If None, any port which can be represented accurately by a dbu representation will be printed in dbu otherwise in um. 'dbu'/'um' will force the printing to enforce one or the other representation | `None` |

## save\_layout\_options

```
save_layout_options(**attributes: Any) -> kdb.SaveLayoutOptions
```

Default options for saving GDS/OAS.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `attributes` | `Any` | Set attributes of the layout save option object. E.g. to save the gds without metadata pass `write_context_info=False` | `{}` |

## update\_default\_trans

```
update_default_trans(new_trans: dict[str, str | int | float | dict[str, str | int | float]]) -> None
```

Allows to change the default transformation for reading a yaml file.
