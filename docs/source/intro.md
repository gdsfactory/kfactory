# Getting Started

As an example we will build a small waveguide and incorporate a circular bend waveguide and connect them.

First let us create some layers. We will use the standard library for this.
Create a `layers.py`. The full one can be downloaded here: [`layers.py`](./layers.py).

Additionally we will create a `kfactory.enclosure.Enclosure`. Enclosures allow to automatically generate claddings with [minkowski sums](https://en.wikipedia.org/wiki/Minkowski_addition) or use a function to apply claddings to a cell or region. This enclosure will add the cladding to the bend we will use later.

```python
import kfactory as kf


class LAYER(kf.LayerEnum):
    SI = (1, 0)
    SIEXCLUDE = (1, 1)


si_enc = kf.utils.LayerEnclosure([(LAYER.SIEXCLUDE, 2000)])
```

This will use the standard Library of KFactory.
A library is the equivalent of a layout object in KLayout and keeps track of the KCells.
It mirrors all the other functionalities of a layout object.

Ports are created with the `kfactory.kcell.KCell.create_port` function. You can either specify a transformation here or specify them in a similar manner to gdsfactory. See the API doc for more information.

Now, let us create a KCell for a waveguide. We will use the `kfactory.kcell.autocell`.
This will make sure that if we call the function multiple times that we do not create multiple cells in the layout.
Addiontally, compared to `kfactory.kcell.cell` it will also automatically name the cells using
the function name,as well as the arguments and keyword arguments of the function.
In the end we will let KFactory take care of the naming of the ports we want to add.
This will allow them to depend on the orientation of the port. This will sort the ports by orientation
(0,1,2,3 -> E,N,W,S) and by ascending x (N/S orientation) respectively y (E/W orientation) coordinates.

First we draw two rectangles centered vertically around the x-axis:
Waveguide Core: A rectangle of the specified length and width is drawn on the LAYER.SI (Silicon) layer. This forms the physical path for light.
Exclusion Zone: A second, slightly wider rectangle (width_exclude) is drawn on the LAYER.SIEXCLUDE layer. This acts as a "keep-out" area, telling the design software or foundry not to place other silicon structures too close to the waveguide, which helps prevent unwanted optical effects.
After that, we define the ports 1 and 2. The first port is rotated by 180 degrees through:
name="1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=LAYER.SI , this makes port 1 face left.
The second port is not rotated and thus faces right.
Lastly, the code cleans up and adds convenience:
c.auto_rename_ports(): This is a convenience function that renames the ports from the temporary names "1" and "2" to a standard convention, like "o1" and "o2" (optical 1 and optical 2), based on their position.
return c: The function returns the completed KCell object, which contains the shapes and ports, ready to be used in a larger design.

```python
from layers import LAYER

import kfactory as kf


@kf.cell
def straight(width: int, length: int, width_exclude: int) -> kf.KCell:
    """Waveguide: Silicon on 1/0, Silicon exclude on 1/1"""
    c = kf.KCell()
    c.shapes(LAYER.SI).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.shapes(LAYER.SIEXCLUDE).insert(
        kf.kdb.Box(0, -width_exclude // 2, length, width_exclude // 2)
    )

    c.create_port(
        name="1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=LAYER.SI
    )
    c.create_port(
        name="2",
        trans=kf.kdb.Trans(0, False, length, 0),
        width=width,
        layer=LAYER.SI,
    )

    c.auto_rename_ports()

    return c


if __name__ == "__main__":
    kf.show(straight(2000, 50000, 5000))
```

The ``kf.show`` will create a GDS in the temp folder and then send the GDS by klive to KLayout (if klive is installed).
By running this with ``python straight.py``, it should show us a straight like this:

![straight](./_static/waveguide.png)

Afterwards let us create the composite cell [`complex_cell.py`](./complex_cell.py). This one incorporates a waveguide and a circular bend and then connects them.

First, a straight function is defined. Then similarly to the above code, ports are added and renamed.
The second portion of this code only runs when executed directly:
It calls the straight function to build a concrete instance of the waveguide with the following dimensions (in database units, where 1000 dbu = 1 µm):
width: 2000 dbu (2.0 µm)
length: 50000 dbu (50.0 µm)
width_exclude: 5000 dbu (5.0 µm)
Display the Result: The kf.show command takes the component that was just built and opens it in the KLayout application viewer. This allows you to visually inspect the final geometry of the waveguide and its exclusion layer.

```python
from layers import LAYER

import kfactory as kf


@kf.cell
def straight(width: int, length: int, width_exclude: int) -> kf.KCell:
    """Waveguide: Silicon on 1/0, Silicon exclude on 1/1"""
    c = kf.KCell()
    c.shapes(LAYER.SI).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.shapes(LAYER.SIEXCLUDE).insert(
        kf.kdb.Box(0, -width_exclude // 2, length, width_exclude // 2)
    )

    c.create_port(
        name="1", trans=kf.kdb.Trans(2, False, 0, 0), width=width, layer=LAYER.SI
    )
    c.create_port(
        name="2",
        trans=kf.kdb.Trans(0, False, length, 0),
        width=width,
        layer=LAYER.SI,
    )

    c.auto_rename_ports()

    return c


if __name__ == "__main__":
    kf.show(straight(2000, 50000, 5000))
```

With `kfactory.kcell.KCell.add_port` an existing port of an instance can be added to the parent cell.
`kfactory.kcell.Instance.connect` allows an instance to be transformed so that one of its ports is connected to another port.

You will get a cell like this:

![complex_cell](_static/complex.png)
