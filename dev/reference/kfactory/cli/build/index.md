# build

CLI interface for kfactory.

Use `kf --help` for more info.

## build

```
build(build_ref: Annotated[str, Argument(default=..., help='The file|module|function to execute:\nAccepted Formats:\n- /path/to/file.py::cell_function_name\n- module.submodule::cell_function_name\n- /path/to/file.py\n- module.submodule')], func_kwargs: Annotated[list[str] | None, Argument(help="Arguments used for --type function. Doesn't have any influence for other types")] = None, show: Annotated[bool, Option(help='Show the file through klive in KLayout')] = True, library: Annotated[list[str] | None, Option(help="Library(s) used by the main layout file. Only works for functions, not for '__main__' modules")] = None, out_dir: Annotated[Path | None, Option(--out - dir, -o, help='Output directory for written layouts. Defaults to build/mask.')] = None, suffix: Annotated[LayoutSuffix, Option(help='Format of the layout files')] = LayoutSuffix.oas, write_full: Annotated[bool, Option(help='Write the gds with full library support. Uses libraries passed with --library. Only works in function mode not on modules')] = True, write_static: Annotated[bool, Option(help='Write a layout where all cells are converted to static (non-library) cells.')] = False, write_nocontext: Annotated[bool, Option(help='Write the layout without any meta infos. This is useful for submitting the GDS to fabs.')] = False, max_vertex_count: Annotated[int, Option(help='Maximum number of vertices per polygon.')] = 4000, max_cellname_length: Annotated[int, Option(help='Maximum number of characters in a cell name.')] = 99) -> None
```

Run a python modules **main** or a function if specified.

## show

```
show(file: Path) -> None
```

Show a GDS or OAS file in KLayout through klive.
