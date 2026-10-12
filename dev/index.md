# KFactory 3.2.2

KFactory is a Python framework for photonic and electronic chip layout, built on [KLayout](<https://klayout.de>)'s C++ geometry engine. It provides parametric cells with caching, optical and electrical routing, enclosures via Minkowski sums, and schematic-driven design with LVS.

## Key Features

- **Cell caching** — the `@kf.cell` decorator deduplicates identical components automatically
- **Routing** — optical and electrical bundle routing, Manhattan primitives, all-angle routing, and path-length matching
- **Cross-sections &amp; enclosures** — define waveguide profiles and automatic boolean cladding layers via Minkowski sums
- **Schematics** — place-and-connect workflow with netlist extraction and layout-vs-schematic verification
- **Virtual cells** — hierarchical logical containers for schematic-driven design
- **Dual coordinate systems** — `KCell` (integer DBU) and `DKCell` (float µm) work side by side
- **KLayout integration** — full access to `kdb.Region`, `kdb.Polygon`, DRC, and GDS/OASIS I/O
- **Jupyter &amp; KLive** — live preview in KLayout while editing notebooks
- **PDK system** — bundle layers, factories, cross-sections, and technology into reusable packages

## Getting Started

### Installation

KFactory is available on [PyPI](<https://pypi.org/project/kfactory/>) and requires Python 3.12+.

```
uv add kfactory

# or with pip
pip install kfactory
```

### Development

```
just dev
```

This installs the development environment and sets up pre-commit hooks.

## Ecosystem

| Package | Description |
| --- | --- |
| [gdsfactory](<https://github.com/gdsfactory/gdsfactory>) | Full-featured chip design framework — KFactory is its layout backend |
| [kfnetlist](<https://github.com/gdsfactory/kfnetlist>) | Standalone netlist extraction and generation |

## Documentation

Full documentation is available at [gdsfactory.github.io/kfactory](<https://gdsfactory.github.io/kfactory>).

Upgrading from an earlier version? See the [migration guide](<https://gdsfactory.github.io/kfactory/dev/docs/source/migration/index.md>).

## License

[MIT](<https://gdsfactory.github.io/kfactory/dev/LICENSE>)

---

- **Getting Started**

  ---

  Install kfactory and build your first component in under 5 minutes.

  ·
- **Core Concepts**

  ---

  Understand KCells, layers, ports, instances, and the DBU ↔ µm coordinate systems.

  ·  ·
- **Routing**

  ---

  Optical and electrical bundle routing, Manhattan primitives, all-angle, and path-length matching.

  ·  ·
- **Components**

  ---

  Straight waveguides, euler/circular bends, tapers, Bezier S-bends, and the factory pattern.

  ·  ·
- **Enclosures**

  ---

  Layer enclosures via Minkowski sums, cross-sections, and KCell-level cladding.

  ·
- **Utilities**

  ---

  Grid layout, packing, DRC fixing, fill, and regression testing.

  ·  ·
- **PDK**

  ---

  Bundle layers, factories, cross-sections, and technology into a reusable PDK.

  ·
- **Schematics**

  ---

  Schematic-driven layout, netlist extraction, LVS, and YAML/JSON round-trips.

  ·
- **How-To Guides**

  ---

  Common patterns, best practices, and a comprehensive FAQ.

  ·
