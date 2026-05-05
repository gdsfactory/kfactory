# %% [markdown]
# # Schematic Cells
#
# This notebook demonstrates how to use `kfactory` for schematic-driven
# photonic design. We will:
# - Build higher-level schematic cells
#     - Create basic parametric cells (PCell) such as straights and bends
#     - Define routing strategies
# - Compare schematic vs. extracted layouts (LVS)
# - Generate reusable code from schematics

# %%
# Imports
import kfactory as kf
import numpy as np

from IPython.core.getipython import get_ipython
from pprint import pformat

# %% editable=true slideshow={"slide_type": ""} tags=["hide"]
# For jupyter to show the big dicts/jsons correctly, we need a helper function `scrollable_text`
# this is hidden from the docs build

from IPython.display import display, HTML
import html



def scrollable_text(
    text: str, max_height: int = 300, width: str = "100%", font_size: str = "14px"
) -> None:
    """Render scrollable, searchable text output for Jupyter and mkdocs-jupyter.

    This function wraps text inside a scrollable <pre> block with a search box.
    It adapts to light/dark mode automatically. The search highlights all matches
    and pressing Enter jumps to the next match.

    Args:
        text (str): The text to display.
        max_height (int, optional): Maximum height in pixels before scrolling.
            Defaults to 300.
        width (str, optional): CSS width (e.g. "100%", "800px").
            Defaults to "100%".
        font_size (str, optional): CSS font size (e.g. "14px", "0.9em").
            Defaults to "14px".
    """
    safe = html.escape(str(text))

    style = (
        f"max-height:{max_height}px; overflow:auto; "
        f"border:1px solid var(--st-border); padding:6px; "
        f"background:var(--st-bg); color:var(--st-fg); "
        f"width:{width}; font-size:{font_size}; white-space:pre-wrap;"
    )

    html_block = f"""
    <style>
    :root {{
        --st-bg: #f9f9f9;
        --st-fg: #111;
        --st-border: #ccc;
    }}
    @media (prefers-color-scheme: dark) {{
        :root {{
            --st-bg: #1e1e1e;
            --st-fg: #ddd;
            --st-border: #555;
        }}
        mark {{
            background: #ffb347;
            color: black;
        }}
    }}
    </style>
    <div style="margin-bottom:0.5em;">
      <input type="search" placeholder="Search (Enter = next match)"
             style="margin-bottom:6px; width:98%; padding:4px;"
             oninput="
                var q=this.value;
                var pre=this.nextElementSibling;
                var orig=pre.dataset.orig;
                pre.dataset.index=0;
                if(!q) {{
                    pre.innerHTML=orig;
                    return;
                }}
                var regex=new RegExp('('+q.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&')+')','gi');
                pre.innerHTML=orig.replace(regex,'<mark>$1</mark>');
                var marks=pre.querySelectorAll('mark');
                if(marks.length) marks[0].scrollIntoView({{behavior:'smooth', block:'center'}});
             "
             onkeydown="
                if(event.key==='Enter'){{
                    event.preventDefault();
                    var pre=this.nextElementSibling;
                    var marks=pre.querySelectorAll('mark');
                    if(!marks.length) return;
                    var idx=parseInt(pre.dataset.index)||0;
                    idx=(idx+1)%marks.length;
                    pre.dataset.index=idx;
                    marks[idx].scrollIntoView({{behavior:'smooth', block:'center'}});
                }}
             ">
      <pre style="{style}" data-orig="{safe}" data-index="0">{safe}</pre>
    </div>
    """
    display(HTML(html_block))

# %% [markdown]
# ## Basic example with routing
#
# In order to avoid name conflicts, let's create a new clean `KCLayout` (our PDK container).
# A **PDK** (Process Design Kit) defines the available layers, devices, and design rules
# for a given process. Here we’ll create a lightweight one for demonstration.

# %%
class Layers(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2,0)

layers = Layers()
pdk = kf.KCLayout("SCHEMA_PDK_ROUTING", infos=Layers)

# %% [markdown]
# ### Cell functions
#
# To begin, we define the **basic building blocks** for routing:
# - A **straight waveguide** of given length and width
# - A **90° Euler bend** for turning corners
#
# These primitives are enough to assemble larger routed networks.

# %%
@pdk.cell
def straight(width: int, length: int) -> kf.KCell:
    c = pdk.kcell()
    c.shapes(layers.WG).insert(kf.kdb.Box(0, -width // 2, length, width // 2))
    c.create_port(
        name="o1",
        width=width,
        trans=kf.kdb.Trans(rot=2, mirrx=False, x=0, y=0),
        layer_info=layers.WG,
    )
    c.create_port(
        name="o2",
        width=width,
        trans=kf.kdb.Trans(x=length, y=0),
        layer_info=layers.WG,
    )

    return c


bend90_function = kf.factories.euler.bend_euler_factory(kcl=pdk)
bend90 = bend90_function(width=0.500, radius=10, layer=layers.WG)

# %% [markdown]
# ### Routing strategy
#
# Next we define a **routing strategy** (`route_bundle`).
# This specifies how to connect groups of ports with straight sections and bends.
# - It ensures separation between parallel routes
# - Reuses our basic cells (`straight`, `bend90`)
# - Can be applied consistently across designs

# %%
@pdk.routing_strategy
def route_bundle(
    c: kf.KCell,
    start_ports: list[kf.Port],
    end_ports: list[kf.Port],
    separation: int = 5000,
) -> list[kf.routing.generic.ManhattanRoute]:
    return kf.routing.optical.route_bundle(
        c=kf.KCell(base=c._base),
        start_ports=[kf.Port(base=sp.base) for sp in start_ports],
        end_ports=[kf.Port(base=ep.base) for ep in end_ports],
        separation=separation,
        straight_factory=straight,
        bend90_cell=bend90,
    )

# %% [markdown]
# ### Example schematic with routing
#
# Now we can demonstrate usage in a schematic:
# - Two straight sections (`s1` and `s2`)
# - Positioned apart vertically
# - Connected automatically by our routing strategy
#
# This shows how schematics carry both connectivity **and** layout placement information.

# %%
@pdk.schematic_cell
def route_example() -> kf.schematic.TSchematic[int]:
    schematic = kf.Schematic(kcl=pdk)

    s1 = schematic.create_inst(
        name="s1", component="straight", settings={"length": 5000, "width": 500}
    )
    s2 = schematic.create_inst(
        name="s2", component="straight", settings={"length": 5000, "width": 500}
    )

    s1.place(x=1000, y=10_000)
    s2.place(x=1000, y=210_000)

    schematic.add_route(
        "s1-s2", [s1["o2"]], [s2["o2"]], "route_bundle", separation=20_000
    )

    return schematic


route_example()

# %% [markdown]
# ## Example: 45 Degrees Crossing with virtual cells
#
# We’ll now construct a more advanced schematic: a **grid of 45° crossings**.
# This introduces:
# - Direct polygon construction
# - Use of virtual parametric cells (`vcell` and `VKCell`)
# - Hierarchical design through schematic instantiation

# %% [markdown]
# ### Setup pdk
#
# Let’s define a new `KCLayout` for this example, including
# a cross-section definition for a wide waveguide.

# %%
pdk = kf.KCLayout("CROSSING_PDK", infos=Layers)

LAYER = Layers()

xs_wg1 = pdk.get_icross_section(
    kf.SymmetricalCrossSection(
        width=1000,
        enclosure=kf.LayerEnclosure(
            [(LAYER.WGEX, 3000)], name="WG", main_layer=LAYER.WG
        ),
        name="WG1000",
    )
)

# Ensure the same cross_section is also available in the target layout as well
kf.kcl.get_icross_section(xs_wg1)

# %% [markdown]
# #### PDK Cells
#
# The `cross` cell builds a single 45° crossing:
# - Constructs polygons for waveguide arms
# - Ensures spacing rules are met via `fix_spacing_tiled`
# - Adds enclosures for cladding / fill excludes
# - Creates ports in four directions for connectivity

# %%
@pdk.cell
def cross(cross_section: str) -> kf.KCell:
    c = pdk.kcell()
    xs = c.kcl.get_icross_section(cross_section)

    # calculate points for one arm of the cross
    points = [
        kf.kdb.DPoint(
            x * 0.075, c.kcl.to_um(xs.width // 2) + float(np.sin(x / 125 * np.pi))
        )
        for x in range(101)
    ]
    mt = kf.kdb.DTrans.M0

    poly = kf.kdb.DPolygon(points + list(reversed([mt * p for p in points]))).to_itype(
        c.kcl.dbu
    )

    center_dist = c.kcl.to_dbu(points[-1].y)

    base_trans = kf.kdb.Trans(-poly.bbox().right - center_dist, 0)

    r = kf.kdb.Region(
        [
            poly.transformed(base_trans) * kf.kdb.Trans(rot, False, 0, 0)
            for rot in range(4)
        ]
    ).hulls()

    shapes = c.shapes(LAYER.WG)
    shapes.insert(r)

    # fix minimum space violations for 300 dbu (.3um)
    fix = kf.utils.fix_spacing_tiled(c, 300, layer=LAYER.WG)

    # remove unfixed polygons
    shapes.clear()

    # add fixed polygon
    shapes.insert(fix)

    bb = c.bbox(c.kcl.layer(xs.main_layer))

    c.create_port(trans=kf.kdb.Trans(0, False, bb.right, 0), cross_section=xs)
    c.create_port(trans=kf.kdb.Trans(1, False, 0, bb.top), cross_section=xs)
    c.create_port(trans=kf.kdb.Trans(2, False, bb.left, 0), cross_section=xs)
    c.create_port(trans=kf.kdb.Trans(3, False, 0, bb.bottom), cross_section=xs)

    xs.enclosure.apply_minkowski_tiled(c, xs.main_layer)

    c.auto_rename_ports()

    return c

# %% [markdown]
# ### Virtual cells
#
# Unlike physical cells, **virtual cells** are defined parametrically:
# - Only generate geometry when needed
# - Lightweight and efficient
#
# Here we define:
# - `bend_euler`: a parametric Euler bend
# - `euler_term`: a bend tapering to a termination
# - `straight`: a parametric straight section

# %%
@pdk.vcell
def bend_euler(
    radius: float,
    cross_section: str,
    angle: float = 90,
    resolution: float = 150,
) -> kf.VKCell:
    """Create a virtual euler bend.

    Args:
        radius: Radius of the backbone. [um]
        cross_section: Name of the CrossSection of the bend.
        angle: Angle of the bend.
        resolution: Angle resolution for the backbone.
    """
    c = pdk.vkcell()
    xs = c.kcl.get_dcross_section(cross_section)

    dbu = c.kcl.dbu

    backbone = kf.factories.virtual.euler.euler_bend_points(
        angle, radius=radius, resolution=resolution
    )

    kf.factories.virtual.utils.extrude_backbone(
        c=c,
        backbone=backbone,
        width=xs.width,
        layer=xs.main_layer,
        enclosure=xs.enclosure,
        start_angle=0,
        end_angle=angle,
        dbu=dbu,
    )

    c.create_port(
        name="o1",
        cross_section=xs,
        dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
    )
    c.create_port(
        name="o2",
        cross_section=xs,
        dcplx_trans=kf.kdb.DCplxTrans(1, angle, False, backbone[-1].to_v()),
    )

    return c


@pdk.vcell
def euler_term(radius: float, cross_section: str, term_width: float) -> kf.VKCell:
    angle = 45
    resolution = 150
    c = pdk.vkcell()
    xs = c.kcl.get_dcross_section(cross_section)
    dbu = c.kcl.dbu
    backbone = kf.factories.virtual.euler.euler_bend_points(
        angle, radius=xs.radius, resolution=resolution
    )
    kf.factories.virtual.utils.extrude_backbone_dynamic(
        c=c,
        backbone=backbone,
        width1=xs.width,
        width2=term_width,
        layer=xs.main_layer,
        enclosure=xs.enclosure,
        start_angle=0,
        end_angle=angle,
        dbu=dbu,
    )

    c.create_port(
        name="o1",
        cross_section=xs,
        dcplx_trans=kf.kdb.DCplxTrans(1, 180, False, backbone[0].to_v()),
    )
    return c


@pdk.vcell
def straight(length: float, cross_section: str) -> kf.VKCell:
    c = pdk.vkcell()
    xs = c.kcl.get_dcross_section(cross_section)

    kf.factories.virtual.utils.extrude_backbone(
        c,
        [kf.kdb.DPoint(0, 0), kf.kdb.DPoint(length, 0)],
        start_angle=0,
        end_angle=0,
        width=xs.width,
        layer=xs.main_layer,
        enclosure=xs.enclosure,
        dbu=c.kcl.dbu,
    )

    c.create_port(
        name="o2",
        dcplx_trans=kf.kdb.DCplxTrans(mag=1, rot=0, mirrx=False, x=length, y=0),
        cross_section=xs,
    )
    c.create_port(
        name="o1",
        dcplx_trans=kf.kdb.DCplxTrans(mag=1, rot=180, mirrx=False, x=0, y=0),
        cross_section=xs,
    )

    return c


# %% [markdown]
# ### Crossing schematic
#
# The `crossing45` schematic builds an array of crossings:
# - Tiles multiple `cross` instances
# - Adds spacers and bends to enforce pitch
# - Places input/output ports systematically
#
# This results in a scalable crossing matrix driven entirely by schematic logic.

# %%
@kf.kcl.schematic_cell(output_type=kf.DKCell)
def crossing45(n: int, pitch: kf.typings.um, cross_section: str) -> kf.DSchematic:
    s = kf.DSchematic(kcl=kf.kcl)

    xs = s.kcl.get_dcross_section(cross_section)

    cross_cell = cross(cross_section=cross_section)

    cross_port_delta = (
        cross_cell.ports["o1"].dcplx_trans.disp
        - cross_cell.ports["o2"].dcplx_trans.disp
    ).length()
    width = cross_cell.dbbox(cross_cell.kcl.layer(xs.main_layer)).width()

    bend_cell = bend_euler(radius=30, cross_section=cross_section, angle=45)

    dy = abs(bend_cell.ports["o1"].y - bend_cell.ports["o2"].y)
    dl = float((pitch - cross_port_delta - dy * 2) / np.sqrt(2))

    d_w = float(pitch * np.sqrt(2) - width)
    if d_w < 0:
        raise ValueError(
            f"Pitch must be bigger than the crossing's size: crossing_width={width}, {pitch=}"
        )

    for i in range(n // 2):
        for j in range(n // 2):
            crossing = s.create_inst(
                name=f"crossing_{i}_{j}",
                component="cross",
                virtual=True,
                kcl=pdk,
                settings={"cross_section": xs.name},
            )

            if d_w > 0:
                match i, j:
                    case 0, 0:
                        crossing.place(orientation=45)
                    case 0, j:
                        wg_ij = s.create_inst(
                            name=f"spacer_{i}_{j}_1",
                            component="straight",
                            settings={"length": d_w, "cross_section": cross_section},
                            kcl=pdk,
                            virtual=True,
                        )
                        wg_ij.connect(
                            "o1", s.instances[f"crossing_{i}_{j - 1}"].ports["o4"]
                        )
                        crossing.connect("o2", wg_ij.ports["o2"])
                    case i, 0:
                        wg_ij = s.create_inst(
                            name=f"spacer_{i}_{j}_2",
                            component="straight",
                            settings={"length": d_w, "cross_section": cross_section},
                            kcl=pdk,
                            virtual=True,
                        )
                        wg_ij.connect(
                            "o1", s.instances[f"crossing_{i - 1}_{j}"].ports["o3"]
                        )
                        crossing.connect("o1", wg_ij.ports["o2"])
                    case i, j:
                        wg_ij1 = s.create_inst(
                            name=f"spacer_{i}_{j}_1",
                            component="straight",
                            settings={"length": d_w, "cross_section": cross_section},
                            kcl=pdk,
                            virtual=True,
                        )
                        wg_ij1.connect(
                            "o1", s.instances[f"crossing_{i}_{j - 1}"].ports["o4"]
                        )
                        wg_ij2 = s.create_inst(
                            name=f"spacer_{i}_{j}_2",
                            component="straight",
                            settings={"length": d_w, "cross_section": cross_section},
                            kcl=pdk,
                            virtual=True,
                        )
                        wg_ij2.connect(
                            "o1", s.instances[f"crossing_{i - 1}_{j}"].ports["o3"]
                        )
                        crossing.connect("o2", wg_ij1.ports["o2"])
                        crossing.connect("o1", wg_ij2.ports["o2"])
            else:
                match i, j:
                    case 0, 0:
                        crossing.place()
                    case 0, j:
                        crossing.connect(
                            "o2", s.instances[f"crossing_{i}_{j - 1}"].ports["o4"]
                        )
                    case i, 0:
                        crossing.connect(
                            "o1", s.instances[f"crossing_{i - 1}_{j}"].ports["o3"]
                        )
                    case i, j:
                        crossing.connect(
                            "o2", s.instances[f"crossing_{i}_{j - 1}"].ports["o4"]
                        )
                        crossing.connect(
                            "o1", s.instances[f"crossing_{i - 1}_{j}"].ports["o3"]
                        )
    for i in range(n // 2):
        spacer_start_top = s.create_inst(
            name=f"io_spacer_{i}",
            component="straight",
            settings={"length": dl, "cross_section": cross_section},
            kcl=pdk,
            virtual=True,
        )
        bend_start_top = s.create_inst(
            name=f"bend45_{i}",
            component="bend_euler",
            settings={"angle": 45, "cross_section": cross_section, "radius": 30},
            kcl=pdk,
            virtual=True,
        )
        bend_start_top.mirror = True
        spacer_start_top.connect("o2", s.instances[f"crossing_{i}_0"].ports["o2"])
        spacer_start_top.connect("o1", bend_start_top.ports["o2"])

        spacer_start_bot = s.create_inst(
            name=f"io_spacer_{n - 1 - i}",
            component="straight",
            settings={"length": dl, "cross_section": cross_section},
            kcl=pdk,
            virtual=True,
        )
        bend_start_bot = s.create_inst(
            name=f"bend45_{n - i - 1}",
            component="bend_euler",
            settings={"angle": 45, "cross_section": cross_section, "radius": 30},
            kcl=pdk,
            virtual=True,
        )
        spacer_start_bot.connect("o2", s.instances[f"crossing_0_{i}"].ports["o1"])
        spacer_start_bot.connect("o1", bend_start_bot.ports["o2"])

        spacer_end_top = s.create_inst(
            name=f"io_spacer_{n + i}",
            component="straight",
            settings={"length": dl, "cross_section": cross_section},
            kcl=pdk,
            virtual=True,
        )
        bend_end_top = s.create_inst(
            name=f"bend45_{n + i}",
            component="bend_euler",
            settings={"angle": 45, "cross_section": cross_section, "radius": 30},
            kcl=pdk,
            virtual=True,
        )
        bend_end_top.mirror = True
        spacer_end_top.connect(
            "o1", s.instances[f"crossing_{i}_{n // 2 - 1}"].ports["o4"]
        )
        spacer_end_top.connect("o2", bend_end_top.ports["o2"])
        spacer_end_bot = s.create_inst(
            name=f"io_spacer_{2 * n - i - 1}",
            component="straight",
            settings={"length": dl, "cross_section": cross_section},
            kcl=pdk,
            virtual=True,
        )
        bend_end_bot = s.create_inst(
            name=f"bend45_{2 * n - i - 1}",
            component="bend_euler",
            settings={"angle": 45, "cross_section": cross_section, "radius": 30},
            kcl=pdk,
            virtual=True,
        )
        spacer_end_bot.connect(
            "o1", s.instances[f"crossing_{n // 2 - 1}_{i}"].ports["o3"]
        )
        spacer_end_bot.connect("o2", bend_end_bot.ports["o2"])

        io_l_start = float(pitch * i)
        io_l_end = float((n // 2 - i - 1) * pitch)
        if io_l_start:
            io_straight_start_top = s.create_inst(
                name=f"io_straight_{i}",
                component="straight",
                settings={"length": io_l_start, "cross_section": cross_section},
                kcl=pdk,
                virtual=True,
            )
            io_straight_start_top.connect("o2", bend_start_top.ports["o1"])
            io_straight_start_bot = s.create_inst(
                name=f"io_straight_{n - 1 - i}",
                component="straight",
                settings={"length": io_l_start, "cross_section": cross_section},
                kcl=pdk,
                virtual=True,
            )
            io_straight_start_bot.connect("o2", bend_start_bot.ports["o1"])

            s.add_port(name=f"in_{n // 2 + i}", port=io_straight_start_top.ports["o1"])
            s.add_port(
                name=f"in_{n // 2 - 1 - i}", port=io_straight_start_bot.ports["o1"]
            )
        else:
            s.add_port(name=f"in_{n // 2 + i}", port=bend_start_top.ports["o1"])
            s.add_port(name=f"in_{n // 2 - 1 - i}", port=bend_start_bot.ports["o1"])
        if io_l_end:
            io_straight_end_top = s.create_inst(
                name=f"io_straight_{n + i}",
                component="straight",
                settings={"length": io_l_end, "cross_section": cross_section},
                kcl=pdk,
                virtual=True,
            )
            io_straight_end_top.connect("o2", bend_end_top.ports["o1"])
            io_straight_end_bot = s.create_inst(
                name=f"io_straight_{2 * n - 1 - i}",
                component="straight",
                settings={"length": io_l_end, "cross_section": cross_section},
                kcl=pdk,
                virtual=True,
            )
            io_straight_end_bot.connect("o2", bend_end_bot.ports["o1"])
            s.add_port(name=f"out_{n // 2 + i}", port=io_straight_end_top.ports["o1"])
            s.add_port(
                name=f"out_{n // 2 - 1 - i}", port=io_straight_end_bot.ports["o1"]
            )
        else:
            s.add_port(name=f"out_{n // 2 + i}", port=bend_end_top.ports["o1"])
            s.add_port(name=f"out_{n // 2 - 1 - i}", port=bend_end_bot.ports["o1"])

    return s

c = crossing45(8, pitch=30, cross_section="WG1000")
c

# %%
scrollable_text(pformat(c.schematic.model_dump(exclude_defaults=True)))

# %% [markdown]
# ### Sample LVS of schematic vs extracted (Connection) Netlist
#
# With both schematic and extracted netlists, we can perform a partial **Layout vs. Schematic (LVS)**:
# - `schematic_netlist`: direct from schematic definition
# - `extracted_netlist`: derived from the physical layout
#
# Matching them ensures the layout faithfully implements the intended connectivity.

# %%
schematic_netlist = c.schematic.netlist()
scrollable_text(pformat(schematic_netlist.model_dump()))

# %%
extracted_netlist = c.netlist()[
    c.name
]  # the extracted netlist is hierarchical by default
scrollable_text(pformat(extracted_netlist.model_dump()))

# %% [markdown]
# Let’s make an LVS check, i.e. compare the extracted netlist versus the netlist directly from the schematic.

# %%
assert schematic_netlist == extracted_netlist

# %% [markdown]
# ## Converting a Schematic to a cell function (parametric cell (PCell))
#
# Another powerful feature: **exporting schematics as code**.
# - `code_str()` generates a self-contained Python function
# - The result is a reusable **parametric cell (PCell)**
# - This makes schematics portable and automatable across environments

# %%
from IPython.display import Code
Code(c.schematic.code_str())

# %% [markdown]
# To avoid name conflicts with our existing schematic,
# let’s make a copy and rename it before execution.

# %%
new_schematic = c.schematic.model_copy()
new_schematic.name = new_schematic.name + "_copy"

# %% [markdown]
# ### Executing generated code
#
# We can directly execute the generated code string in this notebook,
# which defines a new PCell function.
# This closes the loop:
# 1. Design a schematic
# 2. Generate its layout and netlist
# 3. Export as reusable code

# %%
get_ipython().run_cell(new_schematic.code_str())

# %% [markdown]
# Now we can instantiate the newly generated PCell and visualize it.

# %%
c_new = crossing45_N8_P30_CSWG1000_copy()
c_new

# %%
c_new.ports.print()
