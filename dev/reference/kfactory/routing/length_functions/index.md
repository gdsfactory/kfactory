# length\_functions

Length function for calculating length of manhattan routes.

## LengthFunction

Bases: `Protocol`

Protocol for a function which calculates the length of a route.

## get\_length\_from\_area

```
get_length_from_area(layer: LayerInfo | None = None) -> LengthFunction
```

Get length from are in dbu.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `layer` | `LayerInfo \| None` | The layer for which to calculate the area. | `None` |

Returns:

| Type | Description |
| --- | --- |
| `LengthFunction` | Length in dbu. |
