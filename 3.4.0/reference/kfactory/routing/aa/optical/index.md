# optical

Optical routing allows the creation of photonic (or any route using bends).

## OpticalAllAngleRoute

Bases: `BaseModel`

Optical route containing a connection between two ports.

Fields:

- `backbone` (`list[DPoint]`)
- `start_port` (`Port`)
- `end_port` (`Port`)
- `instances` (`list[VInstance]`)
- `length` (`float`)
- `length_straights` (`float`)

## backbone2bundle

```
backbone2bundle(backbone: Sequence[DPoint], port_widths: list[float], spacings: list[float]) -> list[list[kdb.DPoint]]
```

Used to extract a bundle from a backbone.

## route

```
route(c: VKCell | KCell | DKCell, width: float, backbone: Sequence[DPoint], straight_factory: VirtualStraightFactory, bend_factory: VirtualBendFactory, bend_ports: tuple[str, str] = ('o1', 'o2'), straight_ports: tuple[str, str] = ('o1', 'o2'), tolerance: float = 0.1, angle_tolerance: float = 0.0001) -> OpticalAllAngleRoute
```

Places an all-angle route.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `VKCell \| KCell \| DKCell` | The virtual or real KCell to place the route in. | *required* |
| `width` | `float` | width of the rotue (passed to straight\_factory and bend\_factory). The layer the route ports will be extracted from bend port layers. | *required* |
| `backbone` | `Sequence[DPoint]` | The points of the route. | *required* |
| `straight_factory` | `VirtualStraightFactory` | Function to create straights from length and width. \[um\] | *required* |
| `bend_factory` | `VirtualBendFactory` | Function to create bends from length and width. \[um\] | *required* |
| `bend_ports` | `tuple[str, str]` | Names of the ports of the bend to use for connecting straights and bends. | `('o1', 'o2')` |
| `straight_ports` | `tuple[str, str]` | Names of the ports of the straight to use for connecting straights and bends. | `('o1', 'o2')` |
| `tolerance` | `float` | Allow for a small tolerance when placing bends and straights. If the distance is below this tolerance, the route will be placed. | `0.1` |
| `angle_tolerance` | `float` | If a resulting bend from a point in the backbone would have an angle below this tolerance, the point will be skipped and a straight between the point before and the following will be created. | `0.0001` |

## route\_bundle

```
route_bundle(c: KCell | DKCell | VKCell, start_ports: Sequence[DPort | Port], end_ports: Sequence[DPort | Port], backbone: Sequence[DPoint], separation: float | list[float], straight_factory: VirtualStraightFactory, bend_factory: VirtualBendFactory, bend_ports: tuple[str, str] = ('o1', 'o2'), straight_ports: tuple[str, str] = ('o1', 'o2')) -> list[OpticalAllAngleRoute]
```

Places all-angle routes.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell \| DKCell \| VKCell` | The virtual or real KCell to place the route in. | *required* |
| `start_ports` | `Sequence[DPort \| Port]` | Ports denoting the beginning of each route. Must be sorted in anti-clockwise orientation with regards to the desired bundle order. | *required* |
| `end_ports` | `Sequence[DPort \| Port]` | Ports denoting the end of each route. Must be sorted in clockwise orientation with regards to the desired bundle order. | *required* |
| `backbone` | `Sequence[DPoint]` | The points of the route. The router will route to the first point and then create a bundle which follows this points as a backbone. Bends leading the first or following the last backbone point are guaranteed to be outside the backbone. | *required* |
| `separation` | `float \| list[float]` | Minimal separation between each piece of the bundle. This is only guaranteed from the backbone start to backbone end. | *required* |
| `straight_factory` | `VirtualStraightFactory` | Function to create straights from length and width. \[um\] | *required* |
| `bend_factory` | `VirtualBendFactory` | Function to create bends from length and width. \[um\] | *required* |
| `bend_ports` | `tuple[str, str]` | Names of the ports of the bend to use for connecting straights and bends. | `('o1', 'o2')` |
| `straight_ports` | `tuple[str, str]` | Names of the ports of the straight to use for connecting straights and bends. | `('o1', 'o2')` |
