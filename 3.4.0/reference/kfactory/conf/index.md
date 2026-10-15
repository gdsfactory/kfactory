# conf

Kfactory configuration.

## LogFilter

Bases: `BaseModel`

Filter certain messages by log level or regex.

Filtered messages are not evaluated and discarded.

Fields:

- `level` (`LogLevel`)
- `regex` (`str | None`)

### \_\_call\_\_

```
__call__(record: Record) -> bool
```

Loguru needs the filter to be callable.

## LogLevel

Bases: `StrEnum`

KFactory logger levels.

## PROPID

Bases: `IntEnum`

Mapping for GDS properties.

### NAME

```
NAME = 0
```

Instance name.

### PURPOSE

```
PURPOSE = 1
```

Instance purpose (e.g. 'routing').

## Settings

Bases: `BaseSettings`

KFactory settings object.

**Attrs**

n\_threads: Number of threads to use for tiling processor, defaults to all available cores. logger: The loguru class to use for logging. Shouldn't be necessary to configure by hand. logfilter: The filter to use. Can be configured to set log level and filter messages by regex. display\_type: The type of image to show when calling the jupyter display function. meta\_format: Metadata format to use for reading KLayout metadata. If set to 'default', metadata will be read as instances such as Trans/DCplxTrans. If the metadata is in the old string format (there was a bug in how to read metadata in some versions), use 'string'. console: The rich console to use for displaying rich content. max\_cellname\_length: The maximum length of a cell name.

### display\_type

```
display_type: Literal['widget', 'image'] = 'image'
```

The default behavior for displaying cells in jupyter.

### logfilter

```
logfilter: LogFilter = Field(default_factory=LogFilter)
```

Can configure the logger to ignore certain levels or by regex.

### meta\_format

```
meta_format: Literal['v3', 'v2', 'v1'] = 'v3'
```

The format of the saving of metadata.

**Transformations and other KLayout objects are stored as a string. In**

case of ports they are converted back to KLayout objects on read.

v2: All objects can be stored in the nativ KLayout format (klayout\>=0.28.13)

### n\_threads

```
n_threads: int = get_affinity()
```

Number of threads to use for multithreaded operations.

### project\_dir

```
project_dir: Path | None
```

Find the current working directory's project dir.

This is the git repo if it exists, cwd otherwise.

### write\_kfactory\_settings

```
write_kfactory_settings: bool = True
```

Write kfactory version into the gds/oasis.

### \_\_init\_\_

```
__init__(**data: Any) -> None
```

Set log filter and run pydantic.

## add\_traceback

```
add_traceback(record: Record) -> None
```

Add a traceback to the logger.

## get\_affinity

```
get_affinity() -> int
```

Get number of cores/threads available.

On (most) linux we can get it through the scheduling affinity. Otherwise, fall back to the multiprocessing cpu count.

## tracing\_formatter

```
tracing_formatter(record: Record) -> str
```

Traceback filtering.

Filter out frames coming from Loguru internals.
