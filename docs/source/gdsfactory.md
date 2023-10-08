# kfactory vs gdsfactory

kfactory is based on KLayout and therefore has quite a few fundamental differences to gdsfactory.

A Components in gdsfactory corresponds to a [KCell][kfactory.kcell.KCell] in kfactory. ComponentReference is
represented in kfactory as an [Instance][kfactory.kcell.Instance].

## KCLayout / KCell / Instance

KLayout uses a [Layout](https://klayout.de/doc/code/class_Layout.html) object as a base. Cells (and KCells)
must have a Layout as a base, they cannot work without one. Therefore a KCell will always be attached to a
[KCLayout][kfactory.kcell.KCLayout] which is an extension of a Layout object. kfactory provides a default KCLayout objecti
[kfactory.kcl][kfactory.kcell.kcl] which all KCells not specifying another KCLayout in the constructor will use.

This KCLayout object contains all KCells and also keeps track of layers.

Similar as a KCell cannot exist without a KCLayout, an Instance cannot exist without being part of a KCell. It must be created through the KCell

## Layers

Compared to gdsfactory, KLayout needs to initialize new layers. Layers are always associated or part of one KCLayout. They cannot be shared
or used in another KCLayout without a function that specifically copies from one KCLayout to another.
It can either by done directly in the KCLayout object with `kcl.layer(layernumber, datatype)` which will return an integer. This integer
is the internal index of the layer, meaning KLayout will keep layers in a mapping (dictionary) like structure.

kfactory also provides an enum class [LayerEnum][kfactory.kcell.LayerEnum] to do the mapping to the (default) KCLayout. This can either be done in the standard enum way

!!! example "LayerEnum"

    ```python
    class LAYER(kfactory.LayerEnum):
        WG = (1, 0)
        WGEXCLUDE = (1, 1)
    ```

Or it can be done dynamically with a slightly more complex syntax.

!!! example "Dynamic LayerEnum"

    ```python
    LAYER = kfactory.LayerEnum("LAYER", {"WG": (1, 0), "WGEXCLUDE": (1, 1)})
    ```

The first argument represents the name of the enum that will be used for the `__str__` or `__repr__` methods. It is strongly recommended to name it the same as the variable
it is assigned to. This will make sure the behavior is the same as the first construction way.i

The LayerEum also allows mapping from string to layer index and layer number and datatype:

!!! example "Accessing LayerEnum by index or name and getting layer number & datatype"

    ```python-shell
    >>> LAYER = kfactory.LayerEnum("LAYER", {"WG": (1,0), "WGEXCLUDE": (1,1)})
    >>> LAYER.WG
    <LAYER.WG: 0>
    >>> LAYER["WG"]
    <LAYER.WG: 0>
    >>> LAYER(0)
    <LAYER.WG: 0>
    >>> LAYER.WG.datatype
    0
    >>> LAYER.WG.layer
    1
    ```

!!! danger "Layer Indexes"

    In KLayout it is possible to push shapes or other layer associated objects into layer indexes that don't exist (yet or even ever). Therefore always use either the `LayerEnum`
    to access a shapes object or use the KLayout tools too do so. E.g. shapes on layer `(1,0)` can either be accessed with `c.shapes(LAYER.WG)` or `c.shapes(c.kcl.layer(1,0))`.
    It is never good practice to do `c.shapes(0)` even if layer index 0 exists. If you import this module later on, index 0 might be something else, or worse even, be deleted.

## Shapes

In contrast to gdsfactory, every geometrical dimension is represented as an object. All the objects are available in two flavors. Integer based for the mapping to the grid
of gds/oasis in database units (dbu) or floating version based on micrometer.

| Object (dbu) | Object (um)    | Description                                                                                              |
|--------------|----------------|----------------------------------------------------------------------------------------------------------|
| Point        | DPoint         | Holds x/y coordinate in dbu                                                                              |
| Vector       | DVector        | Similar to a point, but can be used for geometry operations and can be multiplied                        |
| Edge         | DEdge          | Connection of two points (p1/p2), is aware of the two sides                                              |
| Box          | DBox           | A rectangle defined through two points. Rotating a box will result in a bigger box                       |
| SimplePolygon| DSimplePolygon | A polygon that has no holes (this is what all polygons will be converted to when inserting)              |
| Polygon      | DPolygon       | Like the simple polygon but this one can have holes and allows operations like sizing                    |
| Text         | DText          | Labels. They can have a full transformations, but KLayout doesn't show full transformations by default   |
| Shape        | -              | A generalized container for other geometric objects that allows storage and retrieval                    |
| Shapes       | -              | A flat collection of shapes. Used by KCells to access shapes in a cell                                   |
| Region       | -              | Flat or deep collection of polygons. Any other dbu shape can be inserted (except Texts)                  |

In kfactory and KLayout these object can live outside of a (K)Cell. Therefore it is not possible to create them through the KCell like in gdsfactory.

These objects can be inserted into a KCell with `c.shapes(layer_index).insert(shabpe_like_object)`.

### gdsfactory's `add_polygon` in kfactory

In gdsfactory polygons are usually created through `c.add_polygon(pts, layer_tuple)`. In kfactory this is not directly possible, nor very useful,
as not all geometrical objects are polygons. Additionally, kfactory and KLayout don't know layers without a datatype and integers alone are interpreted
as layer indexes not as a `(layer_number, 0)` tuple.

In kfactory a `Polygon` can be created like this and then inserted into KCell `c` with `c.shapes(layer_index).insert(polygon)`. Since the objects are not linked
to any KCell, they can be used multiple times. Using the `LAYER` object from above, code could look like this:

!!! example "Polygon"

    ```python
    # dbu based
    points = [kfactory.kdb.Point(x, y) for x, y in [(0, 0), (1000, 0), (500, 500)]]
    polygon = kfactory.kdb.Polygon(points)
    c.shapes(LAYER.WG).insert(polygon)
    c.shapes(LAYER.WGEXCLUDE).insert(polygon)
    # um based
    dpoints = [kfactory.kdb.DPoint(x, y) for x, y in [(0, 0), (1000, 0), (500, 500)]]
    dpolygon = kfactory.kdb.DPolygon(dpoints)
    c.shapes(LAYER.WG).insert(dpolygon)
    c.shapes(LAYER.WGEXCLUDE).insert(dpolygon)
    ```
Due to the verbosity of this code, kfactory provides convenience function for polygons and dpolygons to convert arrays of shap `[n, 2]` into a
`(D)Polygon` directly:

!!! example "Polygon from Array"

    ```python
    # dbu based
    polygon = kfactory.polygon_from_array([(0, 0), (10, 0), (5, 5)])
    c.shapes(LAYER.WG).insert(polygon)
    c.shapes(LAYER.WGEXCLUDE).insert(polygon)
    # um based
    dpolygon = kfactory.dpolygon_from_array([(0, 0), (10, 0), (5, 5)])
    c.shapes(LAYER.WG).insert(dpolygon)
    c.shapes(LAYER.WGEXCLUDE).insert(dpolygon)
    ```

### gdsfactory's `add_label` in kfactory

Similar to the `add_polygon` function, `add_label` as a text record to a cell. Due to the nature of the layer number alone in gdsfactory vs layer index in kfactory,
there is no `add_label` in kfactory. Instead they can be used like any other shape object.

!!! example "Text"

    ```python
    # dbu based
    c.shapes(LAYER.WG).insert(kfactory.kdb.Text("any string here", x_dbu, y_dbu))
    # um based
    c.shapes(LAYER.WG).insert(kfactory.kdb.DText("any string here", x_um, y_um))
    ```

## Connecting Ports

kfactory also offers `c.connect(port_name, other_port)` like gdsfactory does. It doesn't exactly do the same thing as in gdsfactory though. A [Port][kfactory.kcell.Port]
in kfactory will always try to be on grid. Additionally the port is using `kfactory.kdb.Trans` and `kfactory.kdb.DCplxTrans` by default, similar to an instance.
This also means that a port is aware of mirroring. Since a `connect` can be simplified to `instance.trans = other_port.trans * kfactory.kdb.Trans.R180 * port.trans.inversed()`
(for the 90° on-grid cases), it can be seen that the center, angle and mirror flag of the `instance` is overwritten. Therefore, any move / rotation / mirror on the instance
`connect` is called on, will have no influence on the state after the connect.

Also, as with gdsfactory `connect` is not final. It does not imply any shared link between the instances after the `connect`, it is simply a transformation with some checks
about layer, width and port type matching.


!!! example

    ```python
    # inst1,inst2 are instances
    # connect inst1 "o1" to inst2 "o2"
    inst1.connect("o1", inst2.ports["o2"])
    # also possible
    inst1.connect("o1", inst2, "o2")
    ### If inst2 "o2" had trans.is_mirror() == True, inst1's transformation now also has is_mirror() == True
    ```

## LayerEnclosure / KCellEnclosure vs CrossSection

kfactory doesn't have the concept of cross sections. since cross sections are limited to have a path as a backbone, kfactory implemented a more generalized form as enclosures.
[LayerEnclosures][kfactory.enclosure.LayerEnclosure] can use regions or even entire layers as a basis to apply excludes and claddings (or anythin that depends on the base form). Additionally, kfactory has the extended
concept of [KCellEnclosure][kfactory.enclosure.KCellEnclosure]. These can apply enclosures to a whole KCell on all layers the KCellEnclosure is aware of. For further info, please head over to the [Tutorial](/kfactory/notebooks/03_Enclosures)
