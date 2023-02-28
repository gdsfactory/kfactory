# KFactory 0.4.5

Kfactory is a [gdsfactory](https://github.com/gdsfactory/gdsfactory)-like tool. It is built with [KLayout](https://klayout.de) as a backend instead of gdstk, but aims to offer the similar featuers.

Features similar to gdsfactory:

- [x] Cells & decorator for caching & storing cells
- [x] Simple routing (point to point and simpl bundle routes for electrical routes)
- [x] Basic cells like euler/circular bends, taper, waveguide
- [x] Path extrusion (no interface with CrossSections)


Notable missing Features:
- [ ] PDK/package configuration
- [ ] CrossSection
- [ ] Netlist/Schematics and LVS
- [ ] More advanced routing
- [ ] Plugin system (simulations etc.)
- [ ] Jupyter integration


New/Improved Features:
- Fully hierarchical bi-directional conversion to YAML
- Automatic snapping to grid thanks to KLayout
- More features for vector geometries due to concept of Point/Edge/Vector/Polygon from Klayout
- Easy booleans thanks to KLayout Regions
- Enclosures: use the concept of enclosures, similar to cross sections, to allow automatic
  calculation of boolean layers for structures based on [minkowski sum](https://en.wikipedia.org/wiki/Minkowski_addition),
  which are built into KLayout


## Installation

kfactory is available on [pypi](https://pypi.org/project/kfactory/)

```
pip install kfactory
```

At the moment kfactory works only on python 3.10

### Development Installation


A development environment can be installed with

```
python -m pip install .[dev]
```

It is defined in `pyproject.toml`. For committing `pre-commit` should be installed with `pre-commit install`.
