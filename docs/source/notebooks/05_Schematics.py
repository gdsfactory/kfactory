# ---
# jupyter:
#   jupytext:
#     custom_cell_magics: kql
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.17.3
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Schematic Cells

# %%
# Imports
import kfactory as kf
import numpy as np

from IPython.core.getipython import get_ipython
from pprint import pformat

# %% [markdown]
# You can also use multiple KCLayout objects as PDKs or Libraries of KCells and parametric KCell-Functions

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
# In order to avoid name conflicts, let's create a new clean KCLayout (pdk)


# %%
class Layers(kf.LayerInfos):
    WG: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 0)
    WGCLAD: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 0)
    WGEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(1, 1)
    WGCLADEX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(111, 1)
    FILL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(2, 0)
    FILL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(3, 0)
    FILL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(10, 0)
    METAL1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(20, 0)
    METAL2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(22, 0)
    METAL3: kf.kdb.LayerInfo = kf.kdb.LayerInfo(24, 0)
    METAL1EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(20, 1)
    METAL2EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(22, 1)
    METAL3EX: kf.kdb.LayerInfo = kf.kdb.LayerInfo(24, 1)
    VIA1: kf.kdb.LayerInfo = kf.kdb.LayerInfo(21, 0)
    VIA2: kf.kdb.LayerInfo = kf.kdb.LayerInfo(23, 0)


layers = Layers()
pdk = kf.KCLayout("SCHEMA_PDK_ROUTING", infos=Layers)


# %% [markdown]
# ### Cell functions
#
# For routing a basic straight and a bend are sufficient.


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

# %% [markdown]
# ### Setup pdk

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

# %% [markdown]
# #### PDK Cells


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


kf.kcl.get_dcross_section(xs_wg1)
c = crossing45(8, pitch=30, cross_section="WG1000")
c

# %%
scrollable_text(pformat(c.schematic.model_dump(exclude_defaults=True)))

# %% [markdown]
# ### Sample LVS of schematic vs extracted (Connection) Netlist
#
# With a schematic we can relatively easily do full check between the schematic and extracted netlist.
#
# <i>Note: For full (digital) connections extraction and checks more is necessary than simply comparing netlists. In optics it's not sufficient to check purely for connectivity like in digital electronics where we can simplify this with the assumption that any touching metal is connected. Therefore, additional tests like the connectivity check or even full DRC are necessary for better confidence about LVS.</i>

# %%
schematic_netlist = c.schematic.netlist()
scrollable_text(pformat(schematic_netlist.model_dump()))

# %%
extracted_netlist = c.netlist()[
    c.name
]  # the extracted netlist is hierarchical by default
scrollable_text(pformat(extracted_netlist.model_dump()))

# %% [markdown]
# Let's make an LVS check, i.e. compare the extracted netlist versus the netlist directly from the schematic

# %%
assert schematic_netlist == extracted_netlist

# %% [markdown]
# A schematic can also be converted to python code. This allows to first import/draw schematics with external tools such as gdsfactory+ for example and then convert it to a standard cell function (sometimes called PCell, i.e. Parametric Cell)

# %% [markdown]
# ## Converting a Schematic to a cell function (parametric cell (PCell))
#
# The schematic can output and format a code string to generate a valid python file which can regenerate this schematic. Through the `imports` additional imports can be added.

# %%
from IPython.display import Code

Code(c.schematic.code_str())

# %% [markdown]
# In order to not create a name conflict with the cell created above, let's copy an rename the schematic

# %%
new_schematic = c.schematic.model_copy()
new_schematic.name = new_schematic.name + "_copy"

# %% [markdown]
# Let's run this code. We are using a trick to run code in the ipython environment. The code is roughly equivalent to `exec(new_schematic.code_str())`, meaning we are just feeding the code to be directly executed.

# %%
get_ipython().run_cell(new_schematic.code_str())

# %% [markdown]
# As the code has been executed, we can now directly call it by the variable name, create the new cell and create it and visualize it.

# %%
c_new = crossing45_N8_P30_CSWG1000_copy()
c_new

# %%
c_new.ports.print()
