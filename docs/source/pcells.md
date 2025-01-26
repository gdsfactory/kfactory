# Creating PCells

> [PCell](https://en.wikipedia.org/wiki/PCell) stands for parameterized cell.

PCells are a way to create cells that are parameterized by several variables.

In KFactory, with the @cell for `KCell` and `DKCell` or @vcell for `VKCell` you can easily create PCells.

Throughout this tutorial we use this example of a very simple PCell.

```python
import kfactory as kf


@kf.cell
def rectangle(width: int, height: int, layer: int) -> kf.KCell:
    """Create a rectangle with the given width, height and layer.

    Args:
        width: width of the rectangle in dbu
        height: height of the rectangle in dbu
        layer: layer of the rectangle

    Returns:
        KCell with the rectangle
    """
    c = kf.KCell()
    c.shapes(layer).insert(kf.kdb.Box(0, 0, width, height))
    return c


if __name__ == "__main__":
    kcell = rectangle(1000, 1000, kf.kcl.layer(1, 0))
    kcell.show()
```

This PCell is not very useful by itself, but it will be used to illustrate the different ways to create PCells.

In the above example we were working in dbu with the `KCell` class.

But we can also switch to um very easily. Here are some ways we can do this:

1. Use the `to_dkcell` method with the dbu rectangle pcell:
```python
dkcell = rectangle(1000, 1000, kf.kcl.layer(1, 0)).to_dkcell()
dkcell.show()
```

2. Use the `output_type` argument with the `@cell` decorator.
This performs the conversion automatically.

```python
import kfactory as kf


@kf.cell(output_type=kf.DKCell)
def rectangle(width: int, height: int, layer: int) -> kf.KCell:
    """Create a rectangle with the given width, height and layer.

    Args:
        width: width of the rectangle
        height: height of the rectangle
        layer: layer of the rectangle

    Returns:
        KCell with the rectangle
    """
    c = kf.KCell()
    c.shapes(layer).insert(kf.kdb.Box(0, 0, width, height))
    return c


if __name__ == "__main__":
    dkcell = rectangle(1000, 1000, kf.kcl.layer(1, 0))
    dkcell.show()
```

3. Create separate PCells for dbu and um.

```python
import kfactory as kf


@kf.cell
def rectangle_dbu(width: int, height: int, layer: int) -> kf.KCell:
    """Create a rectangle with the given width, height and layer.

    Args:
        width: width of the rectangle in dbu
        height: height of the rectangle in dbu
        layer: layer of the rectangle

    Returns:
        KCell with the rectangle
    """
    c = kf.KCell()
    c.shapes(layer).insert(kf.kdb.Box(0, 0, width, height))
    return c


@kf.cell
def rectangle_um(width: float, height: float, layer: int) -> kf.DKCell:
    """Create a rectangle with the given width, height and layer.

    Args:
        width: width of the rectangle in um
        height: height of the rectangle in um
        layer: layer of the rectangle

    Returns:
        DKCell with the rectangle
    """
    return rectangle_dbu(kf.kcl.to_dbu(width), kf.kcl.to_dbu(height), layer).to_dkcell()


if __name__ == "__main__":
    kcell = rectangle_dbu(1000, 1000, kf.kcl.layer(1, 0))
    kcell.show()
    dkcell = rectangle_um(1, 1, kf.kcl.layer(1, 0))
    dkcell.show()
```

### Complex Example

There might be a case where you want to create a pcell based on another one, but return a different type of cell.
```python
import kfactory as kf


class Layers(kf.kcell.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)


class DKCellSubclass(kf.DKCell):
    pass


kf.kcl.infos = Layers()

straight = kf.factories.straight.straight_dbu_factory(kcl=kf.kcl)

dkcell_straight_factory = kf.cell(output_type=DKCellSubclass)(straight)

if __name__ == "__main__":
    dkcell_straight = dkcell_straight_factory(1000, 5000, Layers().WG)
    assert isinstance(dkcell_straight, DKCellSubclass)
    dkcell_straight.show()

```
