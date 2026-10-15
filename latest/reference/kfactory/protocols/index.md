# protocols

## BoxFunction

Bases: `Protocol`

Protocol for a box function.

Represents bbox/ibbox/dbbox functions.

### \_\_call\_\_

```
__call__() -> BoxLike[T]
```

```
__call__(layer: LayerEnum | int) -> BoxLike[T]
```

```
__call__(layer: LayerEnum | int | None = None) -> BoxLike[T]
```

Call the box function.

## BoxLike

Bases: `Protocol`

Protocol for a box.

Mirrors some functionality of kdb.DBox, kdb.Box, but provides generic types for the units.

### center

```
center() -> PointLike[T]
```

Get the center of the box.

### empty

```
empty() -> bool
```

Check if the box is empty.

### height

```
height() -> T
```

Get the height of the box.

### width

```
width() -> T
```

Get the width of the box.

## PointLike

Bases: `Protocol`

Protocol for a point.

Mirrors some functionality of kdb.DPoint, kdb.Point, but provides generic types for the units.
