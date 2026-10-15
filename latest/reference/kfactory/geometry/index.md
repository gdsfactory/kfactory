# geometry

## DBUGeometricObject

Bases: `GeometricObject[int]`, `ABC`

### mirror

```
mirror(p1: tuple[int, int] = (0, 1000), p2: tuple[int, int] = (0, 0)) -> Self
```

Mirror self at a line.

### mirror\_x

```
mirror_x(x: int = 0) -> Self
```

Mirror self at an y-axis at position x.

### mirror\_y

```
mirror_y(y: int = 0) -> Self
```

Mirror self at an x-axis at position y.

### rotate

```
rotate(angle: int, center: tuple[int, int] | None = None) -> Self
```

Rotate self.

## GeometricObject

Bases: `ABC`

### center

```
center: tuple[T, T]
```

Returns the coordinate center of the bounding box.

### dcenter

```
dcenter: tuple[float, float]
```

Coordinate of the center of the bounding box in um.

### dx

```
dx: float
```

X coordinate of the center of the bounding box in um.

### dxmax

```
dxmax: float
```

Returns the x-coordinate of the right edge of the bounding box.

### dxmin

```
dxmin: float
```

Returns the x-coordinate of the left edge of the bounding box.

### dxsize

```
dxsize: float
```

Returns the width of the bounding box.

### dy

```
dy: float
```

Y coordinate of the center of the bounding box in um.

### dymax

```
dymax: float
```

Returns the y-coordinate of the top edge of the bounding box.

### dymin

```
dymin: float
```

Returns the y-coordinate of the bottom edge of the bounding box.

### dysize

```
dysize: float
```

Returns the height of the bounding box.

### icenter

```
icenter: tuple[int, int]
```

Returns the coordinate center of the bounding box.

### ix

```
ix: int
```

Returns the x-coordinate of the center of the bounding box.

### ixmax

```
ixmax: int
```

Returns the x-coordinate of the right edge of the bounding box.

### ixmin

```
ixmin: int
```

Returns the x-coordinate of the left edge of the bounding box.

### ixsize

```
ixsize: int
```

Returns the width of the bounding box.

### iy

```
iy: int
```

Returns the y-coordinate of the center of the bounding box.

### iymax

```
iymax: int
```

Returns the y-coordinate of the top edge of the bounding box.

### iymin

```
iymin: int
```

Returns the y-coordinate of the bottom edge of the bounding box.

### iysize

```
iysize: int
```

Returns the height of the bounding box.

### x

```
x: T
```

Returns the x-coordinate of the center of the bounding box.

### xmax

```
xmax: T
```

Returns the x-coordinate of the right edge of the bounding box.

### xmin

```
xmin: T
```

Returns the x-coordinate of the left edge of the bounding box.

### xsize

```
xsize: T
```

Returns the width of the bounding box.

### y

```
y: T
```

Returns the y-coordinate of the center of the bounding box.

### ymax

```
ymax: T
```

Returns the y-coordinate of the top edge of the bounding box.

### ymin

```
ymin: T
```

Returns the y-coordinate of the bottom edge of the bounding box.

### ysize

```
ysize: T
```

Returns the height of the bounding box.

### dmirror

```
dmirror(p1: tuple[float, float] = (0, 1), p2: tuple[float, float] = (0, 0)) -> Self
```

Mirror self at a line.

### dmirror\_x

```
dmirror_x(x: float = 0) -> Self
```

Mirror self at an y-axis at position x.

### dmirror\_y

```
dmirror_y(y: float = 0) -> Self
```

Mirror self at an x-axis at position y.

### dmove

```
dmove(destination: tuple[float, float]) -> Self
```

```
dmove(origin: tuple[float, float], destination: tuple[float, float] | None = None) -> Self
```

```
dmove(origin: tuple[float, float], destination: tuple[float, float] | None = None) -> Self
```

Move self in um.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `tuple[float, float]` | reference point to move | *required* |
| `destination` | `tuple[float, float] \| None` | move origin so that it will land on this coordinate | `None` |

### dmovex

```
dmovex(destination: float) -> Self
```

```
dmovex(origin: float, destination: float | None = None) -> Self
```

```
dmovex(origin: float, destination: float | None = None) -> Self
```

Move self in x-direction in um.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `float` | reference point to move | *required* |
| `destination` | `float \| None` | move origin so that it will land on this coordinate | `None` |

### dmovey

```
dmovey(destination: float) -> Self
```

```
dmovey(origin: float, destination: float | None = None) -> Self
```

```
dmovey(origin: float, destination: float | None = None) -> Self
```

Move self in y-direction in um.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `float` | reference point to move | *required* |
| `destination` | `float \| None` | move origin so that it will land on this coordinate | `None` |

### drotate

```
drotate(angle: float, center: tuple[float, float] | None = None) -> Self
```

Rotate self by a given angle in degrees.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `angle` | `float` | angle to rotate self | *required* |
| `center` | `tuple[float, float] \| None` | reference point to rotate around | `None` |

### imirror

```
imirror(p1: tuple[int, int] = (0, 1000), p2: tuple[int, int] = (0, 0)) -> Self
```

Mirror self at a line.

### imirror\_x

```
imirror_x(x: int = 0) -> Self
```

Mirror self at an y-axis at position x.

### imirror\_y

```
imirror_y(y: int = 0) -> Self
```

Mirror self at an x-axis at position y.

### imove

```
imove(destination: tuple[int, int]) -> Self
```

```
imove(origin: tuple[int, int], destination: tuple[int, int] | None = None) -> Self
```

```
imove(origin: tuple[int, int], destination: tuple[int, int] | None = None) -> Self
```

Move self in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `tuple[int, int]` | reference point to move \[dbu\] | *required* |
| `destination` | `tuple[int, int] \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### imovex

```
imovex(destination: int) -> Self
```

```
imovex(origin: int, destination: int | None = None) -> Self
```

```
imovex(origin: int, destination: int | None = None) -> Self
```

Move self in x-direction in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `int` | reference point to move \[dbu\] | *required* |
| `destination` | `int \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### imovey

```
imovey(destination: int) -> Self
```

```
imovey(origin: int, destination: int | None = None) -> Self
```

```
imovey(origin: int, destination: int | None = None) -> Self
```

Move self in y-direction in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `int` | reference point to move \[dbu\] | *required* |
| `destination` | `int \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### irotate

```
irotate(angle: int, center: tuple[int, int] | None = None) -> Self
```

Rotate self in increments of 90°.

### mirror

```
mirror(p1: tuple[T, T] = ..., p2: tuple[T, T] = ...) -> Self
```

Mirror self at a line.

### mirror\_x

```
mirror_x(x: T = ...) -> Self
```

Mirror self at an y-axis at position x.

### mirror\_y

```
mirror_y(y: T = ...) -> Self
```

Mirror self at an x-axis at position y.

### move

```
move(destination: tuple[T, T]) -> Self
```

```
move(origin: tuple[T, T], destination: tuple[T, T]) -> Self
```

```
move(origin: tuple[T, T], destination: tuple[T, T] | None = None) -> Self
```

Move self in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `tuple[T, T]` | reference point to move \[dbu\] | *required* |
| `destination` | `tuple[T, T] \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### movex

```
movex(destination: T) -> Self
```

```
movex(origin: T, destination: T) -> Self
```

```
movex(origin: T, destination: T | None = None) -> Self
```

Move self in x-direction in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `T` | reference point to move \[dbu\] | *required* |
| `destination` | `T \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### movey

```
movey(destination: T) -> Self
```

```
movey(origin: T, destination: T) -> Self
```

```
movey(origin: T, destination: T | None = None) -> Self
```

Move self in y-direction in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `origin` | `T` | reference point to move \[dbu\] | *required* |
| `destination` | `T \| None` | move origin so that it will land on this coordinate \[dbu\] | `None` |

### rotate

```
rotate(angle: T, center: tuple[T, T] | None = None) -> Self
```

Rotate self.

## SizeInfo

### \_\_init\_\_

```
__init__(bbox: BoxFunction[T]) -> None
```

Initialize this object.

## UMGeometricObject

Bases: `GeometricObject[float]`, `ABC`

### mirror

```
mirror(p1: tuple[float, float] = (0, 1), p2: tuple[float, float] = (0, 0)) -> Self
```

Mirror self at a line.

### mirror\_x

```
mirror_x(x: float = 0) -> Self
```

Mirror self at an y-axis at position x.

### mirror\_y

```
mirror_y(y: float = 0) -> Self
```

Mirror self at an x-axis at position y.

### rotate

```
rotate(angle: float, center: tuple[float, float] | None = None) -> Self
```

Rotate self.
