# generic

Generic routing functions which are independent of the potential use.

## ManhattanRoute

Bases: `BaseModel`

Optical route containing a connection between two ports.

**Attrs**

backbone: backbone points start\_port: port at the first instance denoting the start of the route end\_port: port at the last instance denoting the end of the route instances: list of the instances in order from start to end of the route n\_bend90: number of bends used length: length of the route without the bends length\_straights: length of the straight\_factory elements

Fields:

- `backbone` (`list[Point]`)
- `start_port` (`Port`)
- `end_port` (`Port`)
- `instances` (`list[Instance]`)
- `n_bend90` (`int`)
- `n_taper` (`int`)
- `bend90_radius` (`dbu`)
- `taper_length` (`dbu`)
- `length_straights` (`dbu`)
- `polygons` (`dict[LayerInfo, list[Polygon]]`)
- `length_function` (`LengthFunction`)

### length\_backbone

```
length_backbone: dbu
```

Length of the backbone in dbu.

### taper\_length

```
taper_length: dbu = 0
```

Length of backbone without the bends.

## PlacerFunction

Bases: `Protocol`

A placer function. Used to place Instances given a path.

### \_\_call\_\_

```
__call__(c: KCell, p1: Port, p2: Port, pts: Sequence[Point], route_width: int | None = None, **kwargs: Any) -> ManhattanRoute
```

Implementation of the function.

## check\_collisions

```
check_collisions(c: KCell, start_ports: Sequence[BasePort], end_ports: Sequence[BasePort], routers: Sequence[ManhattanRouter], routes: Sequence[ManhattanRoute], on_collision: Literal['error', 'show_error'] | None = 'show_error', collision_check_layers: Sequence[LayerInfo] | None = None) -> None
```

Checks for collisions given manhattan routes.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `c` | `KCell` | The KCell to check. | *required* |
| `start_ports` | `Sequence[BasePort]` | Ports from which the routes are supposed to start. | *required* |
| `end_ports` | `Sequence[BasePort]` | Ports where the routes are supposed to end. | *required* |
| `routers` | `Sequence[ManhattanRouter]` | The ManhattanRouters that constructed the routes. | *required* |
| `routes` | `Sequence[ManhattanRoute]` | The ManhatnnaRoutes which were used by the placer. | *required* |
| `on_collision` | `Literal['error', 'show_error'] \| None` | What to do on error. Can either do nothing (None), throw an error ("error"), or throw an error and open the cell with report in Klayout ("show\_error"). | `'show_error'` |
| `collision_check_layers` | `Sequence[LayerInfo] \| None` | Sequence of layers which should be checked for overlaps to determine error. If not defined, all layers occurring in ports will be used. | `None` |

## get\_radius

```
get_radius(ports: Sequence[ProtoPort[Any]]) -> dbu
```

Calculates a radius between two ports.

This can be used to determine the radius of two bend ports.

Parameters:

| Name | Type | Description | Default |
| --- | --- | --- | --- |
| `ports` | `Sequence[ProtoPort[Any]]` | A sequence of exactly two ports. | *required* |

Returns:

| Type | Description |
| --- | --- |
| `dbu` | Radius in dbu. |

Raises:

| Type | Description |
| --- | --- |
| `ValueError` | Radius cannot be determined |

## route\_bundle

```
route_bundle(*, c: KCell, start_ports: list[BasePort], end_ports: list[BasePort], route_width: dbu | list[dbu] | None = None, on_collision: Literal['error', 'show_error'] | None = 'show_error', on_placer_error: Literal['error', 'show_error'] | None = 'show_error', collision_check_layers: Sequence[LayerInfo] | None = None, routing_function: ManhattanBundleRoutingFunction = route_smart, routing_kwargs: dict[str, Any] | None = None, placer_function: PlacerFunction, placer_kwargs: dict[str, Any] | None = None, asymmetric_placer_function: PlacerFunction | None = None, asymmetric_placer_kwargs: dict[str, Any] | None = None, constraints: Sequence[Constraint] | None = None, starts: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, ends: dbu | list[dbu] | list[Step] | list[list[Step]] | None = None, start_angles: int | list[int] | None = None, end_angles: int | list[int] | None = None, route_debug: RouteDebug | None = None, route_name: str | None = None) -> list[ManhattanRoute]
```

Route a bundle from starting ports to end\_ports.

Waypoints will create a front which will create ports in a 1D array. If waypoints are a transformation it will be like a point with a direction. If multiple points are passed, the direction will be invfered. For orientation of 0 degrees it will create the following front for 4 ports:

```
      │
      │
      │
      p1 ->
      │
      │
      │


      │
      │
      │
      p2 ->
      │
      │
      │
  ___\waypoint
     /
      │
      │
      │
      p3 ->
      │
      │
      │


      │
      │
      │
      p4 ->
      │
      │
      │
```

Parameters:

<table>       <thead>         <tr>           <th>Name</th>           <th>Type</th>           <th>Description</th>           <th>Default</th>         </tr>       </thead>       <tbody>           <tr class="doc-section-item">             <td>                 <code>c</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.kcell.KCell" optional="">KCell</autoref></code>             </td>             <td>               <div class="doc-md-description">                 <p>Cell to place the route in.</p>                </div>             </td>             <td>                 <em>required</em>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>start_ports</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.port.BasePort" optional="">BasePort</autoref>]</code>             </td>             <td>               <div class="doc-md-description">                 <p>List of start ports.</p>                </div>             </td>             <td>                 <em>required</em>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>end_ports</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.port.BasePort" optional="">BasePort</autoref>]</code>             </td>             <td>               <div class="doc-md-description">                 <p>List of end ports.</p>                </div>             </td>             <td>                 <em>required</em>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>route_width</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref> | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Width of the route. If None, the width of the ports is used.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>on_collision</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="typing.Literal" optional="">Literal</autoref>['error', 'show_error'] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Define what to do on routing collision. Default behaviour is to open send the layout of c to klive and open an error lyrdb with the collisions. &quot;error&quot; will simply raise an error. None will ignore any error.</p>                </div>             </td>             <td>                   <code>'show_error'</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>on_placer_error</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="typing.Literal" optional="">Literal</autoref>['error', 'show_error'] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>If a placing of the components fails, use the strategy above to handle the error. show_error will visualize it in klayout with the intended route along the already placed parts of c. Error will just throw an error. None will ignore the error.</p>                </div>             </td>             <td>                   <code>'show_error'</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>collision_check_layers</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="collections.abc.Sequence" optional="">Sequence</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="klayout.db.LayerInfo" optional="">LayerInfo</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Layers to check for actual errors if manhattan routes detect potential collisions.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>routing_function</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.manhattan.ManhattanBundleRoutingFunction" optional="">ManhattanBundleRoutingFunction</autoref></code>             </td>             <td>               <div class="doc-md-description">                 <p>Function to place the routes. Must return a corresponding list of OpticalManhattan routes. Must accept the following protocol: <div class="highlight"><pre><span></span><code>routing_function(&#10;    c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs&#10;)&#10;</code></pre></div></p>                </div>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.manhattan.route_smart" optional="">route_smart</autoref></code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>routing_kwargs</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="dict" optional="">dict</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="str" optional="">str</autoref>, <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="typing.Any" optional="">Any</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Additional kwargs passed to the placer_function.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>placer_function</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.generic.PlacerFunction" optional="">PlacerFunction</autoref></code>             </td>             <td>               <div class="doc-md-description">                 <p>Function to place the routes. Must return a corresponding list of OpticalManhattan routes. Must accept the following protocol: <div class="highlight"><pre><span></span><code>placer_function(&#10;    c: KCell, p1: Port, p2: Port, pts: list[Point], **placer_kwargs&#10;)&#10;</code></pre></div></p>                </div>             </td>             <td>                 <em>required</em>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>placer_kwargs</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="dict" optional="">dict</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="str" optional="">str</autoref>, <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="typing.Any" optional="">Any</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Additional kwargs passed to the placer_function.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>asymmetric_placer_function</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.generic.PlacerFunction" optional="">PlacerFunction</autoref> | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Placer for routes with asymmetric endpoint profiles. Required if any endpoint is asymmetric. Selection happens per route after port sorting; symmetric routes use placer_function.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>asymmetric_placer_kwargs</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="dict" optional="">dict</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="str" optional="">str</autoref>, <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="typing.Any" optional="">Any</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Arguments for the asymmetric placer, independent of placer_kwargs.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>constraints</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="collections.abc.Sequence" optional="">Sequence</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.schematic.Constraint" optional="">Constraint</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Routing constraints to enforce after routing but before placement. Each constraint's <code>enforce</code> method is called with the routers and routing kwargs (e.g. separation, bend90_radius).</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>starts</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref> | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref>] | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.steps.Step" optional="">Step</autoref>] | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.steps.Step" optional="">Step</autoref>]] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>List of steps to use on each starting port or all of them.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>ends</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref> | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.typings.dbu" optional="">dbu</autoref>] | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.steps.Step" optional="">Step</autoref>] | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" hover="" identifier="kfactory.routing.steps.Step" optional="">Step</autoref>]] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>List of steps to use on each end port or all of them.</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>start_angles</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="int" optional="">int</autoref> | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="int" optional="">int</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Overwrite the port orientation of all start_ports together (single value) or each one (list of values which is as long as start_ports).</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>           <tr class="doc-section-item">             <td>                 <code>end_angles</code>             </td>             <td>                   <code><autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="int" optional="">int</autoref> | <autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="list" optional="">list</autoref>[<autoref backlink-anchor="kfactory.routing.generic.route_bundle" backlink-type="used-by" identifier="int" optional="">int</autoref>] | None</code>             </td>             <td>               <div class="doc-md-description">                 <p>Overwrite the port orientation of all start_ports together (single value) or each one (list of values which is as long as end_ports).</p>                </div>             </td>             <td>                   <code>None</code>             </td>           </tr>       </tbody>     </table>

Returns:

| Type | Description |
| --- | --- |
| `list[ManhattanRoute]` | List of ManattanRoutes containing the instances of the route. |

Raises:

| Type | Description |
| --- | --- |
| `PlacerError` | Something went wrong and the resulting route of the placer function is not manhattan or the elements cannot be fitted. |
| `ValueError` | Ports or places or args are misconfigured. |
