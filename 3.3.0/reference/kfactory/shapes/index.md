# shapes

## VShapes

Emulate `[klayout.db.Shapes][klayout.db.Shapes]`.

### \_\_init\_\_

```
__init__(cell: VKCell, _shapes: Sequence[ShapeLike] | None = None) -> None
```

Initialize the shapes.

### \_\_iter\_\_

```
__iter__() -> Iterator[ShapeLike]
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s __iter__'`.

### bbox

```
bbox() -> kdb.DBox
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s bbox'`.

### clear

```
clear() -> None
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s clear'`.

### each

```
each() -> Iterator[ShapeLike]
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s each'`.

### insert

```
insert(shape: ShapeLike) -> None
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s insert'`.

### size

```
size() -> int
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s size'`.

### transform

```
transform(trans: Trans | DTrans | ICplxTrans | DCplxTrans) -> VShapes
```

Emulate `[klayout.db.Shapes][klayout.db.Shapes]'s transform'`.
