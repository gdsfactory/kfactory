# KFactory

**KFactory** is a Python layout framework built on [KLayout](https://klayout.de).
It is the backend for [gdsfactory](https://github.com/gdsfactory/gdsfactory) and can be used as a
standalone photonic/electronic layout tool.

KFactory exposes KLayout's full geometry engine (boolean regions, Minkowski expansions, DRC) through a clean Python API while adding cell caching, enclosures, all-angle routing, and schematic-driven design.

---

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Getting Started**

    ---

    Install kfactory and build your first component in under 5 minutes.

    [:octicons-arrow-right-24: Installation](getting_started/installation.md)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Quickstart](getting_started/quickstart.py)

-   :material-book-open-variant:{ .lg .middle } **Core Concepts**

    ---

    Understand KCells, layers, ports, instances, and the DBU ↔ µm coordinate systems.

    [:octicons-arrow-right-24: KCell](concepts/kcell.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Layers](concepts/layers.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Ports](concepts/ports.py)

-   :material-transit-connection-variant:{ .lg .middle } **Routing**

    ---

    Optical and electrical bundle routing, Manhattan primitives, all-angle, and path-length matching.

    [:octicons-arrow-right-24: Overview](routing/overview.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Optical](routing/optical.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: All-Angle](routing/all_angle.py)

-   :material-shape:{ .lg .middle } **Components**

    ---

    Straight waveguides, euler/circular bends, tapers, Bezier S-bends, and the factory pattern.

    [:octicons-arrow-right-24: Overview](components/overview.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: PCells](components/pcells.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Factories](components/factories.py)

-   :material-layers:{ .lg .middle } **Enclosures**

    ---

    Layer enclosures via Minkowski sums, cross-sections, and KCell-level cladding.

    [:octicons-arrow-right-24: Cross-Sections](enclosures/cross_sections.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Layer Enclosure](enclosures/layer_enclosure.py)

-   :material-tools:{ .lg .middle } **Utilities**

    ---

    Grid layout, packing, DRC fixing, fill, and regression testing.

    [:octicons-arrow-right-24: Grid](utilities/grid.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: DRC Fix](utilities/drc_fix.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Fill](utilities/fill.py)

-   :material-package-variant:{ .lg .middle } **PDK**

    ---

    Bundle layers, factories, cross-sections, and technology into a reusable PDK.

    [:octicons-arrow-right-24: Creating a PDK](pdk/creating_pdk.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Layer Stack](pdk/technology.py)

-   :material-sitemap:{ .lg .middle } **Schematics**

    ---

    Schematic-driven layout, netlist extraction, LVS, and YAML/JSON round-trips.

    [:octicons-arrow-right-24: Overview](schematics/overview.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: Netlist & I/O](schematics/netlist.py)

-   :material-lightbulb-on:{ .lg .middle } **How-To Guides**

    ---

    Common patterns, best practices, and a comprehensive FAQ.

    [:octicons-arrow-right-24: Best Practices](howto/best_practices.py)
    &nbsp;·&nbsp;
    [:octicons-arrow-right-24: FAQ](howto/faq.md)

</div>

---

## Key Features

- **Cell caching** — `@kf.cell` deduplicates identical components automatically
- **DBU + µm APIs** — `KCell` (integer DBU) and `DKCell` (float µm) work side by side
- **Enclosures** — Minkowski-sum cladding and annular boolean layers, tile-parallelised
- **Bundle routing** — optical and electrical, all-angle, path-length matching, obstacle avoidance
- **Cross-sections** — registered per `KCLayout`; composable with enclosures
- **Schematics** — place-and-connect workflow with netlist extraction and LVS
- **KLayout integration** — full access to `kdb.Region`, `kdb.Polygon`, DRC, and GDS/OASIS I/O
- **klive** — live preview in KLayout while editing notebooks

## Comparison with gdsfactory

See [gdsfactory.md](gdsfactory.md) for a side-by-side feature comparison and migration notes.
