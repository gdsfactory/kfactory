# simplify

Simplifying functions.

## dsimplify

```
dsimplify(points: list[DPoint], tolerance: float) -> list[kdb.DPoint]
```

Simplify a list of um points to a certain tolerance (in um).

Uses [Ramer-Douglas-Peucker algorithm](<https://en.wikipedia.org/wiki/Ramer–Douglas–Peucker_algorithm>)

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `points` | `list[DPoint]` | list of `klayout.db.DPoint` to simplify | *required* |
| `tolerance` | `float` | if two points are \> tolerance (in um) apart, delete most suitable points. | *required* |

## simplify

```
simplify(points: list[Point], tolerance: float) -> list[kdb.Point]
```

Simplify a list of `klayout.db.Point` to a certain tolerance (in dbu).

Uses [Ramer-Douglas-Peucker algorithm](<https://en.wikipedia.org/wiki/Ramer–Douglas–Peucker_algorithm>)

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `points` | `list[Point]` | list of points to simplify | *required* |
| `tolerance` | `float` | if two points are \> tolerance (in dbu) apart, delete most suitable points. | *required* |
