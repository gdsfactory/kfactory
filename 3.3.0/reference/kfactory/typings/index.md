# typings

## dbu

```
dbu = Annotated[int, 'dbu']
```

Integer in database units.

## deg

```
deg = Annotated[float, 'deg']
```

Float in degrees.

## layer

```
layer = Annotated['int | LayerEnum', 'layer']
```

Integer or enum index of a Layer.

## rad

```
rad = Annotated[float, 'rad']
```

Float in radians.

## um

```
um = Annotated[float, 'um']
```

Float in micrometer.

## Angle

```
Angle = int
```

Integer in the range of `[0,1,2,3]` which are increments in 90°.

## Unit

```
Unit = int | float
```

Database unit or micrometer.

## KCellSpecDict

Bases: `TypedDict`

Specification for a KCell.

## MarkerConfig

Bases: `TypedDict`

Configure marker to send through the show function.

**Attrs**

color: 0xffffff type of color as int \[default: None (let klayout decide)\] dismissable: bool whether dismissable \[default: True\] dither\_pattern: dither pattern to use \[default: None (let klayout decide)\] frame\_color: 0xffffff type of color as int \[default: None (let klayout decide)\] halo: halo value \[default: -1 (klayout default is applied)\] frame\_color: 0xffffff type of color as int \[default: None (let klayout decide)\] line\_style: line style to show \[default: None (let klayout decide)\] line\_style: line width to show \[default: 1\] vertex\_size: size of vertices \[default: 1\]
