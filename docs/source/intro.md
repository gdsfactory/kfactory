# Getting Started

As an example we will build a small waveduide and instantiate a circular bend waveguide and connect them.

First let's create some layers. We will use the standard library for this.
Create a `layers.py`. The full one can be downloaded here: [`layers.py`](./layers.py).

Additionally we will create a `kfactory.enclosure.Enclosure`. Enclosures allow to automatically generate claddings with minkosky sums or use a function to apply claddings to a cell or region. This enclosure will add the cladding to the bend we will use later.

```python
import kfactory as kf


class LAYER(kf.LayerEnum):
    SI = (1, 0)
    SIEXCLUDE = (1, 1)


si_enc = kf.utils.LayerEnclosure([(LAYER.SIEXCLUDE, 2000)])
```

This will use the standard Library of KFactory.
A Library is the equivalent of a Layout object in KLayout and keeps track of the KCells.
It mirrors all the other functionalities of a Layout object.

Ports are created with the `kfactory.kcell.KCell.create_port` function. You can either specify a transformation as here or specify them in a similar manner to gdsfactory. See the API doc for more information.

Now, let's create a KCell for a waveguide. We will use the `kfactory.kcell.autocell`.
This will make sure that if we call the function multiple times that we don't create multiple cells in the layout.
Addiontally, compared to `kfactory.kcell.cell` it will also automatically name the cells using
the function name and the arguments and keyword arguments of the function.
In the end we will let KFactory take care of the naming of the ports we want to add.
This will allow them depending on the orientation of the port. This will sort the ports by orientation
(0,1,2,3 -> E,N,W,S) and by ascending x (N/S orientation) respectively y (E/W orientation) coordinates.

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
By running this with ``python straight.py``, this should show us a straight like this:

![straight](./_static/straight.png)

Afterwards let's create the composite cell [`complex_cell.py`](./complex_cell.py). This one instantiates a waveguide and a circular bend and then connects them.

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

With `kfactory.kcell.KCell.add_port` an existing port of an instance can be added to the parent cell. `kfactory.kcell.Instance.connect` allows an instance to be transformed so that one of its ports is connected to another port.

You will get a cell like this:

![complex_cell](_static/complex.png)
