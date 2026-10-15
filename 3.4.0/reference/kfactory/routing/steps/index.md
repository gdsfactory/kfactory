# steps

Classes used for steps in routers.

## Left

Bases: `Step`

Let the router go left.

If a size is given, the router will continues that amount (including the added bend). If include\_bend is true, the router will stop before the next bend needs to bed placed at size's point.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Make the router turn left and go straight if necessary.

## Right

Bases: `Step`

Let the router go right.

If a size is given, the router will continues that amount (including the added bend). If include\_bend is true, the router will stop before the next bend needs to bed placed at size's point.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Adds the bend and potential straight after.

## Step

Bases: `ABC`

Abstract base for a routing step.

### include\_bend

```
include_bend: bool | None
```

Whether the execute should leave space at the end of the step for a bend.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Executes the step.

## Steps

Bases: `RootModel[list[Any]]`

Collection of steps. Runs the execution on them.

### execute

```
execute(router: ManhattanRouterSide) -> None
```

Run all the steps on the given router.

## Straight

Bases: `Step`

Adds a straight section to the router.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Adds a straight section to the router.

## X

Bases: `Step`

Go to an absolute X coordinate.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Adds a straight section to the router.

## XY

Bases: `Step`

Go to an absolute XY coordinate.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Executes the step on a router.

## Y

Bases: `Step`

Go to an absolute X coordinate.

### execute

```
execute(router: ManhattanRouterSide, include_bend: bool) -> None
```

Adds a straight section to the router.
