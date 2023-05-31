# kfactory vs gdsfactory

kfactory is based on KLayout and therefore has quite a few fundamental differences to gdsfactory.

A Components in gdsfactory corresponds to a [KCell][kfactory.kcell.KCell] in kfactory. ComponentReference is
represented in kfactory as an [Instance][kfactory.kcell.Instance].

# KCLayout / KCell / Instance

KLayout uses a [Layout](https://klayout.de/doc/code/class_Layout.html) object as a base. Cells (and KCells)
must have a Layout as a base, they cannot work without one. Therefore a KCell will always be attached to a
[KCLayout][kfactory.kcell.KCLayout] which is an extension of a Layout object. kfactory provides a default KCLayout objecti
[kfactory.kcl][kfactory.kcell.kcl] which all KCells not specifying another KCLayout in the constructor will use.

This KCLayout object contains all KCells and also keeps track of layers.

Similar as a KCell cannot exist without a KCLayout, an Instance cannot exist without being part of a KCell. It must be created through the KCell

# Layers

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
    LAYER = kf.LayerEnum("LAYER", {"WG": (1, 0), "WGEXCLUDE": (1, 1)})
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

# Shapes

In contrast to gdsfactory, every geometrical dimension is represented as an object. All the objects are available in two flavors. Integer based for the mapping to the grid
of gds/oasis in database units (dbu) or floating version based on micrometer.

| Object (dbu) | Object (um) | Description                                                                                              |
|--------------|-------------|----------------------------------------------------------------------------------------------------------|
| Point        | DPoint      | Holds x/y coordinate in dbu                                                                              |
| Vector       | DVector     | Similar to a point, but can be used for geometry operations and can be multiplied                        |
| Edge         | DEdge       | Connection of two points (p1/p2), is aware of the two sides                                              |
| Box          | DBox        | A rectangle defined through two points. Rotating a box will result in a bigger box                       |
| SimplePolygon| DSimplePolygon| A polygon that has no holes (this is what all polygons will be converted to when inserting)            |
| Polygon      | DPolygon    | Like the simple polygon but this one can have holes and allows operations like sizing                    |
| Shape        | -             | A generalized container for other geometric objects that allows storage and retrieval                  |
| Shapes       | -             | A flat collection of shapes. Used by KCells to access shapes in a cell                                 |
| Region       | -             | Flat or deep collection of polygons. Any other dbu shape can be inserted (except Texts)                |
