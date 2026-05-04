# Plan: Split route_bundle into Plan + Place Phases for Backbone Postprocessing

## Context

The constraint-based routing system on the `add-constraints` branch introduces `RoutingConstraint` and `PathLengthMatch` to modify backbones before placement. However, the current `route_bundle()` function runs the entire pipeline atomically: **route -> constrain -> place**. There is no way for a user to:

1. Generate backbones across multiple `route_bundle` calls
2. Inspect and postprocess those backbones together (e.g., pathlength matching across bundles)
3. Then trigger placement

This plan splits `route_bundle()` into two explicit phases and adds an optional postprocessor callback.

---

## Approach: Split `route_bundle` + Optional Callback

### New API

```python
# Phase 1: Generate backbones (route + constrain)
plan = kf.routing.optical.route_bundle_plan(c, start_ports, end_ports, separation=5000, bend90_cell=bend90)

# User modifies plan.routers[i].start.pts here

# Phase 2: Place instances from (possibly modified) backbones
routes = kf.routing.optical.route_bundle_place(c, plan, straight_factory=sf, bend90_cell=bend90)
```

For single-bundle convenience:
```python
routes = kf.routing.optical.route_bundle(
    ...,
    backbone_postprocessor=lambda routers: my_modification(routers),
)
```

Existing `route_bundle()` calls remain unchanged (no new required parameters).

---

## Files to Modify

### 1. `src/kfactory/routing/generic.py` (core changes)

**Add `RouteBundlePlan` dataclass** (~line 60, before `RoutingConstraint`):
```python
@dataclass
class RouteBundlePlan:
    """Intermediate result from route_bundle_plan: routers + resolved ports."""
    routers: list[ManhattanRouter]
    start_ports: list[BasePort]
    end_ports: list[BasePort]
```

**Add `route_bundle_plan()` function:**
- Extract lines 418-529 from `route_bundle()` (argument normalization, `routing_function()` call, port mapping via `start_mapping`/`end_mapping`, and `constraint.enforce()` calls)
- Signature: same routing-related params as `route_bundle()` (no placer params, no collision params)
- Returns `RouteBundlePlan`

**Add `route_bundle_place()` function:**
- Extract lines 530-587 from `route_bundle()` (placement loop, error handling, collision check, constraint route registration)
- Takes `RouteBundlePlan` + placer params + collision/error params
- Returns `list[ManhattanRoute]`

**Refactor `route_bundle()`:**
- Rewrite body to call `route_bundle_plan()` then `route_bundle_place()`
- Add optional `backbone_postprocessor: Callable[[list[ManhattanRouter]], None] | None = None` param
- Call postprocessor between plan and place if provided
- Exact same external behavior for all existing callers

**Update `__all__`:** Add `RouteBundlePlan`, `route_bundle_plan`, `route_bundle_place`

### 2. `src/kfactory/routing/optical.py` (optical wrappers)

**Add `route_bundle_plan()` optical wrapper:**
- Mirrors the existing optical `route_bundle()` signature but only includes routing-related params (separation, bend90_cell for radius extraction, bboxes, waypoints, sort_ports, bbox_routing, starts, ends, angles, constraints)
- No placer-specific params (straight_factory, taper_cell, min_straight_taper, place_port_type, etc.)
- Handles KCell/DKCell unit conversion for routing params
- Calls `generic.route_bundle_plan()` internally

**Add `route_bundle_place()` optical wrapper:**
- Takes `RouteBundlePlan` + placer-specific params (straight_factory, bend90_cell, taper_cell, etc.) + collision params
- Handles KCell/DKCell unit conversion for placer params
- Calls `generic.route_bundle_place()` internally

**Add `backbone_postprocessor` param to existing `route_bundle()`**

### 3. `src/kfactory/routing/__init__.py` (exports)

Add re-exports: `RouteBundlePlan`, `route_bundle_plan`, `route_bundle_place` from generic.

### 4. `tests/test_routing.py` (tests)

- **Split workflow test:** Call `route_bundle_plan()`, modify a router's backbone, call `route_bundle_place()`, verify route reflects modification
- **Callback test:** Pass `backbone_postprocessor` to `route_bundle()`, verify it runs
- **Cross-bundle test:** Two `route_bundle_plan()` calls, postprocess routers from both together, place both
- **Backward compat:** Existing tests pass unchanged

### 5. `src/kfactory/schematic.py` (no changes needed)

The schematic level already handles cross-bundle constraints via the `Constraint` base class: `enforce()` accumulates routers across named routes, then acts when all routes have been seen. For users who want manual postprocessing at the schematic level, they can register a custom `routing_strategy` that internally uses `route_bundle_plan()` + modification + `route_bundle_place()`.

---

## Implementation Notes

- **Port mapping bridge:** The `start_mapping`/`end_mapping` dicts (generic.py lines 511-521) that resolve routers back to their original ports must be computed in `route_bundle_plan()` and stored in `RouteBundlePlan.start_ports` / `end_ports` (already ordered to match routers).

- **Constraint `routes` dict assignment** (generic.py line 586) stays in `route_bundle_place()` since it needs the placed `ManhattanRoute` objects.

- **`route_debug`** parameter goes to `route_bundle_plan()` (it's used by the routing function, not the placer).

- **`name`** parameter is needed in both plan and place: plan uses it for `constraint.enforce(route_name=name)`, place uses it for `constraint.routes[name]`.

---

## Verification

1. Run existing test suite: `pytest tests/test_routing.py` -- all existing tests must pass unchanged
2. New tests exercise the split workflow and callback
3. Manually verify that a cross-bundle pathlength matching example works with the new API
