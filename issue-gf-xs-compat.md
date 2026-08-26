# Make kfactory cross sections the cross-section type gdsfactory returns

## Goal

`gf.cross_section(...)` returns a **kfactory** cross section directly —
`SymmetricalCrossSection` when the profile is mirror-symmetric about the centerline,
`AsymmetricalCrossSection` otherwise. `gf.CrossSection` and `gf.Section` are deleted, not
translated. Round-tripping then comes for free: the cross section a PDK hands out *is* the
one written to and read back from the layout, so

```
gf.cross_section(...) -> GDS/OAS -> the same kfactory cross section
```

holds by construction rather than by a bridge staying in sync.

Today the bridge in `gdsfactory/pdk.py:535` throws away everything except the main
section's width/layer/radius, and gdsfactory keeps its real cross-section state in a
process-local PDK registry that dies with the process — anything not registered in the PDK
(any `xs.copy(width=...)`) cannot be reconstructed from a GDS at all.

This shapes what belongs in the model. A cross section is a *transverse profile*:
ordered strips of `(layer, section_min, section_max)`, plus `name`, `radius`,
`radius_min`, `bbox_sections`. Everything gdsfactory currently hangs off `Section`
(`port_names`, `port_types`, `simplify`, `insets`, `hidden`, `width_function`,
`skip_transition`) is an argument to the *extruder*, and the extruder's output is already
persisted as what it produced — shapes as shapes, ports as ports, each port carrying its
own derived cross section. So none of it enters the profile. What it does mean is that
gdsfactory's extrusion entry points have to grow the parameters that used to ride along on
the cross section; see "What gdsfactory has to change".

## Which repo does what

Most of this plan is gdsfactory work. kfactory's share is bounded and sits entirely in the
cross-section model and its serialization:

| kfactory change                                                        | where | size |
|------------------------------------------------------------------------|-------|------|
| `bbox_sections` never reach the file; `__eq__`/`__hash__` disagree (B6) | `enclosure.py:679`, `:602`, `:691` | small, independent bugfix |
| Add `get_sections()` resolving either type to absolute strips (§2)      | `cross_section.py` | small, additive |
| Optional: helper deriving a section's own cross section for ports (B8)  | `cross_section.py` | small, could live in gdsfactory instead |
| Docs/tests: name stability vs `str(LayerInfo)` (B9), the µm→dbu rule (§3) | — | small |

That is the whole kfactory side, and only the first item is a defect. Everything the plan
originally wanted to change in the model turned out to be intentional and stays: overlapping
same-layer strips keep collapsing (B2), section order stays meaningless (B3), the symmetric
type keeps edge-relative enclosure storage (B4), registration keeps canonicalisation and
non-identifying radius (§4), and the serialization format is unchanged apart from the
`bbox_sections` fix. Odd widths already work via the asymmetric type, and the
port/cross-section invariant (B8) needs no `Port` change.

Everything else is gdsfactory: deleting `CrossSection`/`Section`, returning the kfactory
type from `gf.cross_section()`, and porting roughly 80 call sites (28 `add_bbox`,
21 `.sections`, 13 `.copy(width=…)`, 7 `validate_radius`, 4 `width_function`, 5 radius
overrides) plus the 30 preset factories.

## How persistence works today (kfactory side)

- `KCLayout.set_meta_data` writes one meta entry per registered cross section
  (`kfactory:cross_section:<name>` / `kfactory:asymmetrical_cross_section:<name>`),
  `layout.py:2442`.
- Ports store only the cross-section *name*, `kcell.py:1760`; on read the name is resolved
  against the layout-level registry, `kcell.py:1871`.

So the round trip is only ever as good as the cross-section model itself. That model is
currently missing most of what gdsfactory puts in a cross section.

## Evidence

Survey of all 30 cross sections registered in `gdsfactory.cross_section.cross_sections`
(generic PDK, gdsfactory @ `a9d5817`):

| feature used                                         | presets |
|------------------------------------------------------|--------:|
| per-section `port_names`                              |   30/30 |
| named sections                                        |   27/30 |
| more than one section                                 |   20/30 |
| section `offset != 0` (needs asymmetric)              |   15/30 |
| same layer used by several sections                   |   13/30 |
| mixed `port_types` within one xs                      |    4/30 |
| section `simplify`                                    |    2/30 |
| `bbox_layers`                                         |    1/30 |
| `width_function` / `offset_function`                  |    0/30 |
| `insets`                                              |    0/30 |
| `components_along_path`                               |    0/30 |
| off-grid section edges @ 1 nm dbu                     |    0/30 |
| odd-nm main width (→ asymmetric, see mapping rule)    |    0/30 |

Six presets have same-layer sections that overlap and so get unioned by
`_normalize_sections`: `l_wg_doped_with_trenches`, `l_with_trenches`, `pn_with_trenches`,
`pn_with_trenches_asymmetric`, `rib_heater_doped_via_stack`, `strip_nitride_tip`. In every
case the overlap is an aux strip against the core, and the core is stored separately
(`width` in the symmetric type, the main strip in the asymmetric one), so the union is
geometry-only and lossless — see B2. `strip_nitride_tip`'s `tip_nitride` sits entirely
inside `_default` on the same layer and is therefore geometrically redundant to begin with.

Structural duplicates that today raise `CrossSectionNamingConflictError` on registration:
- `metal3` and `metal_routing` — byte-identical in every respect: geometry, radius,
  radius_min, section name, port config. Only the cross-section name differs. This one is
  irreducible; no change to what counts as "structure" can separate them.
- `strip` / `strip_no_ports` / `rib_bbox` — same geometry, differing in
  `radius_min` / `bbox_layers` / `port_names`. `rib_bbox` is separated by its bbox.
  `strip_no_ports` is not: with port information out of the model (§1) and radius
  non-identifying (§4) it is structurally identical to `strip`, and since its only reason
  to exist was `port_names=("", "")`, it stops being a distinct profile — see §4.

gdsfactory already carries a `try/except CrossSectionNamingConflictError` + warning
workaround for exactly this in `gdsfactory/read/import_gds.py:58`.

Confirmed data loss inside kfactory alone (no gdsfactory involved):

```python
xs = SymmetricalCrossSection(width=500, enclosure=LayerEnclosure(
    sections=[(SLAB, 3000)], main_layer=WG, bbox_sections=[(BOX, 2000)], name="enc_test"))
# write -> read
xs2.bbox_sections   # {}      (was {BOX (3/0): 2000})
xs2 == xs           # False
```

`LayerEnclosure`'s `@model_serializer` (`enclosure.py:679`) emits only
`name`/`sections`/`main_layer`, so `bbox_sections` never reach the file, while `__eq__`
(`enclosure.py:602`) and `unnamed_key` (`enclosure.py:722`) do include them — and
`__hash__` (`enclosure.py:691`) does not. This is a plain bug independent of gdsfactory.

## Blockers, and the ones that turned out not to be

Kept in full because "we looked at this and it is deliberate" is the useful part of the
record. Only **B6** is a defect. **B5** and **B9** need no code change, just gdsfactory
adapting and some docs. **B1, B2, B3, B4, B7** are none — each was a proposed model change
that investigation showed to be either unnecessary or actively wrong.

**B1 — none. A cross section is geometry, and `CrossSectionLayer` already is that.**
This started as "kfactory needs per-section `name`/`port_names`/`port_types`, 30/30 presets
depend on them". Tracing every read site killed it: all of that is extrusion-time, and the
things extrusion produces — a cell's shapes and a cell's ports — are persisted in their own
right, so nothing has to be recovered from the profile afterwards. Kept as a record of why
each field was rejected:

- The `port_names` / `port_types` **pairs are start/end of the extruded path**, not a
  property of the transverse profile: `path.extrude` walks the sections in order and, for
  each truthy `port_names[i]`, emits a port named exactly that at the path start (`i=0`) or
  end (`i=1`), with *that section's* width and layer, `port_types[i]`, centered on *that
  section's* band. So the cross section alone determines the port set (`slot` → 6 ports
  from 3 sections).
- Both pairs are provably never used asymmetrically. Across all 104 sections of the 30
  presets: `port_types[0] != port_types[1]` in **0** sections, and **0** sections name one
  end but not the other. A section either carries ports at both ends or at neither, of one
  type. The pairs are redundant — see §1.
- Every read site in gdsfactory, exhaustively: `port_names`/`port_types` are read at
  `path.py:1081-1082` (`extrude`) and `path.py:1414-1415` (`extrude_transition`) — **two
  sites, both extrusion, nothing else in the codebase**. They are not an accessor for
  "the ports of a cross section" (a cross section has no ports); they are what `extrude`
  should call the two ports of the component it builds. Everything downstream then looks
  those up on the *component*.
- Section `name` is auto-generated when absent — `s_<md5(str(input_dict))[:8]>`
  (`cross_section/base.py:125`), hashed over the raw pre-validation input dict, so it is
  not reproducible from a reconstructed section. Its only functional use is
  `_get_named_sections` (`path.py:966`), called solely from `extrude_transition`
  (`path.py:1392`) to pair sections of two cross sections by name (fallback: layer name;
  duplicates raise). Everything else indexes sections **positionally** — `sections[0]` for
  the main section, `sections[1:]` for the rest (`taper.py:90`, `wire.py:216`,
  `straight.py:41`, `coupler_broadband.py:99`, `taper_from_csv.py:57`).
  `CrossSection.__getitem__` (`xs["name"]`) has **zero** call sites in gdsfactory.

- `simplify` is likewise an argument to the extruder. It changes the polygon that gets
  written, but the polygon *is* what gets written — a component round trip carries the
  simplified shapes as shapes. Nothing needs to re-derive them from the profile.
- Whether a section carries ports does not need recording either. A port is a first-class
  persisted object with its own cross section: to put a port on a section you recenter that
  section and give the port the minimal cross section for it (B8). The port is then the
  record that the section was port-bearing — stored on the cell, where ports live.

Net: a section needs `layer`, `section_min`, `section_max`. Nothing else — which is exactly
what makes `gf.cross_section()` able to return the kfactory type instead of wrapping it,
and what makes the existing normalization (B2) lossless.

**B2 — none. Collapsing overlapping same-layer strips is correct and stays.**
`_normalize_sections` (`cross_section.py:348`) unions touching/overlapping strips on a
layer, and that is the right primitive: extruding one band is cleaner than extruding two
overlapping ones and unioning afterwards. Measured on a 90° arc (core `[-0.25, 0.25]`
nested in slab `[-2.55, 2.55]`, 1 nm dbu), pre-merged vs. separate-then-union differ by
432–832 dbu² from independent edge snapping, and at radius 2.0 µm — narrower than the slab
half-width — the separate-bands version leaves a self-overlapping region whose `area()`
double-counts. One band per layer avoids all of it.

The earlier worry that this destroys the port-bearing core was wrong: **the main strip is
never part of the merge.** In `AsymmetricalCrossSection` the merge runs over `sections`
only, leaving `layer`/`section_min`/`section_max` untouched; in `SymmetricalCrossSection`
the core is the separate `width` field on `main_layer`. Verified — a core `[-250, 250]` with
a trench `[-6750, 250]` on the same layer keeps `width == 500`, and two overlapping *aux*
strips `[-2550,-1550]` + `[-2050,-1050]` correctly collapse to `[-2550,-1050]`.

Combined with sections carrying no metadata (B1), collapsing is now lossless by
construction: there is no name, no port and no identity on a strip for a union to lose.

**B3 — none.** Aux sections are a set of bands per layer; their order carries no meaning
once sections hold no metadata, and the main strip is a separate field rather than
`sections[0]`. Sorting them is fine.

**B4 — none. Edge-relative storage in the symmetric type is intentional and stays.**
`SymmetricalCrossSection` stores non-core layers as a `LayerEnclosure`, i.e. bands relative
to the core edge, and that is the semantics a PDK actually wants: cladding keeps its
relative size as the core changes. Verified — a 3 µm SLAB band sits at ±3.25 µm for a
500 nm core and ±3.55 µm for an 1100 nm core, rather than staying pinned to an absolute
offset. This makes `copy(width=…)` behave the way a process designer means it, and it is
gdsfactory's absolute-offset behaviour that is the odd one out (see "What gdsfactory has to
change").

What is missing is only a *retrieval*: nothing exposes the resolved absolute sections of a
symmetric cross section. That is an additive accessor, not a storage change — see §2.

**B5 — two explicitly named cross sections cannot share a structure.** Scoped precisely:
`_register` (`cross_section.py:1269`) already resolves an *unnamed* cross section onto a
matching canonical entry even when that entry is named, so structural coincidence alone is
harmless — that is what makes the derived cores in B8 free. The one reachable failure is
**two explicitly named** cross sections with the same structure, and via the gdsfactory
bridge every cross section arrives named (the function name, or `xs_<md5>` for a derived
one), so this is the normal path, not a corner.

`_resolve_radius` (`cross_section.py:324`) is a near-dead branch by comparison: it needs an
*unnamed* incoming carrying an explicit radius, which a named gdsfactory factory never
produces.

Neither gets a kfactory change. Both rules are deliberate and gdsfactory adapts (§4):
`metal_routing` becomes an alias *of* `metal3` rather than a second name for one structure,
and radius overrides move from `xs.copy(radius=…)` to the bend/route call. The
`import_gds.py:58` workaround is then deleted rather than generalised.

**B6 — `bbox_sections` are dropped on write** for symmetric cross sections (see above),
plus the `__eq__`/`__hash__` inconsistency.

**B7 — none.** Was "nowhere to put `simplify`/`hidden`/`insets`"; they are extruder
arguments and the extruder's output is persisted as shapes, so they need no home in the
profile (B1).

**B8 — a port on a non-main section needs its own cross section (resolved).** kfactory's
`Port.width` *is* `any_cross_section.width` (`port.py:678`) — a port cannot have a width
independent of the cross section it points at. gdsfactory hands every port the whole cross
section and takes width/center from the owning section, so `slot` yields six ports of two
different widths at three different offsets, all referencing one 0.5 µm cross section.

The fix needs no change to `Port`: **derive a cross section from the section itself** — a
single core of width `section_max - section_min` on that section's layer, centered on its
own midpoint. The section's offset from the path centerline becomes part of the *port
transform*, where offsets belong, not part of the cross section. Measured over the 30
presets:

- Only **4 of 33** port-bearing sections are non-main at all (`slot`'s two rails, the
  HEATER section of `strip_heater_metal` and `strip_heater_metal_undercut`), so this is a
  rare path.
- A non-zero offset does **not** make the derived cross section asymmetric. The offset is a
  port *position* — a y-displacement at rotation 0 — so the cross section stays a
  centered core. `slot`'s left rail spans `[20, 250]` dbu: derived cross section is a
  symmetric 230 dbu core, port at `Trans(0, False, 0, 135)`. Verified.
- The only thing that can force asymmetry is **odd width**: the section center
  `(section_min + section_max) / 2` is an integer exactly when the span is even, so an odd
  span (e.g. `[20, 251]`, center 135.5) has no on-grid center to place the port at. **0 of
  33** port-bearing sections in the generic PDK are odd, so every derived cross section
  there is symmetric.

It also does not proliferate cross sections, which was the objection: the 33 sections
collapse to **12** distinct `(layer, width)` cores that dedupe against cross sections the
PDK already has — derived `(HEATER, 2.5 µm)` *is* `heater_metal`, and `(WG, 0.5 µm)` is
shared by 16 sections including `strip`. That dedupe needs no new machinery and does not
depend on B5: a derived core is unnamed and carries no radius, and `_register`
(`cross_section.py:1289`) already returns the canonical entry for a matching unnamed
structure even when that entry is named. Verified — registering a named `heater_metal`
(2.5 µm HEATER, radius 2.5 µm) and then the derived bare core returns the *same object*,
named `heater_metal`, with no conflict and without `_resolve_radius` firing
(cf. `test_symmetric_unnamed_resolves_to_named`).

The semantics are also the ones you want — routing out of a heater's `e1` extrudes a 2.5 µm
HEATER wire, rather than dragging the WG core along with it.

**B9 — auto-names hash `str(LayerInfo)`** (`_asym_auto_name`, `cross_section.py:303`).
Names are only stable across layouts if layer names are. Worth documenting/validating,
since the port→xs link in the GDS is by name.

## What gdsfactory has to change

Deleting `gf.CrossSection` means every attribute and method call sites make on it must
either exist on the kfactory type, become a free function, or move to the extruder. Counted
outside `gdsfactory/cross_section/`:

| gdsfactory API              | uses | disposition                                        |
|-----------------------------|-----:|----------------------------------------------------|
| `.width`, `.layer`          | 81, 82 | already on the kfactory type ✓                   |
| `.radius`, `.radius_min`    | 30, 2 | already on the kfactory type ✓                    |
| `.name`                     |   11 | already on the kfactory type ✓                     |
| `.add_bbox(component)`      |   28 | free function `add_bbox(c, xs)` — only reads `bbox_sections`, no kfactory change |
| `.sections`                 |   21 | needs one shape across sym/asym (today symmetric returns `dict[layer, [(min,max)]]`, asymmetric a tuple) — §2 |
| `.copy(width=…)`            |   13 | needs explicit "replace main width, keep other sections' absolute bounds" semantics — B4(c) |
| `.validate_radius(r)`       |    7 | free function or a small method; reads `radius_min` only |
| `.components_along_path`    |    1 | drop (holds live `Component` refs)                 |
| `.mirror()`, `.hash`, `.append_sections()`, `.bbox_layers`, `.bbox_offsets` | 0 | drop, dead API |

And the fields that lose their home when `Section` dies:

- `port_names` / `port_types` → convention. Walking port-bearing sections in order with a
  per-type counter reproduces **33/33** preset port-name pairs, and the type is derivable
  from the layer (no layer in the 30 presets carries both optical and electrical
  port-bearing sections). The `cross_section(port_names=…)` parameter goes away — this is
  the change that touches every preset signature.
- `simplify` → `extrude()` already takes a global `simplify`; only the per-section variant
  is lost, which costs `rib`/`rib2` their cladding-only tolerance (2/30).
- `width_function` / `offset_function` → `extrude()` arguments. **This is the real port
  work**: `xs.copy(width_function=…)` is load-bearing in
  `polarization_splitter_rotator.py:83`, `mmi2x2_with_sbend.py:38`,
  `mmi1x2_with_sbend.py:61` and `straight_piecewise.py:54`. Parametric width is a genuine
  capability; it just isn't a property of a profile.
- `insets`, `hidden`, `skip_transition` → extruder/transition arguments; one real consumer
  (`taper_cross_section.py:68`).
- `Section.name` → transitions pair sections by name today (`_get_named_sections`,
  `path.py:966`). With unnamed sections, pair positionally or by layer.
- `Transition` / `TransitionAsymmetric` stay gdsfactory-side: they pair two cross sections
  at extrusion time and are never carried by a port.
- `CrossSection.mirror()` — a mirrored profile is just another cross section built with
  negated bounds; no mirror flag is ever stored on a cross section (mirror lives on
  instance/port transforms).
- gdsfactory's derived `xs_<md5>` naming — the kfactory name is stored data, not recomputed.

Nothing here removes a capability outright; the parametric-width and transition paths just
move from the profile to the call that uses it.

## Proposed design

### 1. The section type is unchanged: layer + absolute signed bounds

```python
class CrossSectionSection(BaseModel, frozen=True):   # today's CrossSectionLayer
    layer: kdb.LayerInfo
    section_min: dbu            # signed, absolute, relative to the profile centerline
    section_max: dbu
```

Three fields, which is what `CrossSectionLayer` already has. Nothing from gdsfactory's
`Section` gets added. The rule that gets us here: **a cross section describes a transverse
profile; everything else is an argument to the extruder, and the extruder's output is
already persisted as the thing it produced.**

- Shapes are persisted as shapes, so `simplify`, `hidden` and `insets` need no home in the
  profile — a component round trip carries the simplified polygon itself.
- Ports are persisted as ports, each with its own cross section, so "does this section
  carry ports" needs no home either. To put a port on a section, recenter that section and
  give the port the minimal cross section for it (B8); the port is then the record.
- Port names and types are what the extruder calls what it made; downstream code reads them
  off the component. If a generator wants the gdsfactory convention it can regenerate it —
  walking port-bearing sections in order with a per-type counter reproduces **33/33**
  preset port-name pairs exactly, including `slot` (`o1,o2` / `o3,o4` / `o5,o6`) and
  `strip_heater_metal` (`o1,o2` then `e1,e2`) — but that belongs to the generator, not the
  profile.

What the section list still owes: **order** (so `sections[0]` remains the main section for
`width`/`layer`/`main_layer`) and **no collapsing of overlaps** (B2).

### 2. Two types, two representations, plus a shared retrieval

Both types stay exactly as they are stored today. `SymmetricalCrossSection` and
`AsymmetricalCrossSection` are separate types because they carry different connection
semantics — the asymmetric one drives the mirror rules in `connect()` — and each stores what
suits it:

- **Symmetric**: `width` on `main_layer`, other layers as edge-relative `LayerEnclosure`
  bands. Relative is the point: cladding scales with the core (B4).
- **Asymmetric**: main strip as `layer`/`section_min`/`section_max`, aux strips as absolute
  signed `sections`, normalized per layer (B2).

The only addition is a **retrieval that resolves either type to its absolute sections**, so
callers that need the realised profile do not have to know which storage they got:

```python
def get_sections(self) -> tuple[CrossSectionSection, ...]:
    """Absolute signed dbu strips, main strip first, enclosure bands resolved
    against the current core width."""
```

For the symmetric type it resolves each enclosure band against `width` — a 3 µm SLAB band
becomes `[-3250, 3250]` at a 500 nm core and `[-3550, 3550]` at 1100 nm. For the asymmetric
type it is main strip + `sections`. That single accessor is what gdsfactory's 21 `.sections`
call sites bind to, and it is additive: no storage change, no serialization change, no
change to how either type compares or hashes.

### 3. µm → dbu and the symmetric/asymmetric choice

The `width % 2 == 0` rule on `SymmetricalCrossSection` stays as is — an odd-dbu profile
simply is not symmetric about the centerline, and the asymmetric type is what expresses it.
The mapping rule is therefore mechanical, with no new capability required:

Each section edge is rounded to dbu independently, via `kcl.to_dbu`:
`section_min = to_dbu(offset - width/2)`, `section_max = to_dbu(offset + width/2)`.

Per-edge, not width-and-offset-separately: rounding the two inputs first and computing the
edges afterwards can still land an edge on a half-dbu (`width=0.501, offset=0` → `±250.5`)
and needs a second rounding anyway. Rounding the edges directly makes both grid-aligned by
construction, makes the derived width `section_max - section_min` exactly representable,
and makes the mapping idempotent — re-applying it to an already-rounded profile is a no-op,
which is what keeps the round trip stable.

The tie-breaking rule is **half away from zero**, because that is what `kcl.to_dbu` already
does — it is `kdb.CplxTrans(dbu).inverted() * value`, i.e. KLayout's own rounding
(`layout.py:888`). Measured at `dbu=0.001`: `0.0005 → 1`, `-0.0005 → -1`, `0.2505 → 251`,
`-0.2505 → -251`. Python's `round()` would give `0, 0, 250, -250`. Do not introduce a
second rounding rule for cross sections — one convention per codebase.

It also happens to be the correct choice on the merits, because it is antisymmetric:
`to_dbu(-x) == -to_dbu(x)`, so a profile that is mirror-symmetric in µm is still
mirror-symmetric in dbu and stays a `SymmetricalCrossSection`. The trap to avoid is naive
half-up (`floor(x + 0.5)`), which sends `-250.5 → -250` and `+250.5 → +251`: the profile
silently becomes asymmetric and changes type. The cost of half-away-from-zero is a mild
outward bias — a strip with both edges on a tie grows by 1 dbu per side — which is
deterministic, idempotent, and preferable to a symmetry-breaking rule.

There are then **two separate** symmetric/asymmetric decisions; do not conflate them.

1. *For the whole profile*: mirror-symmetric about `x = 0` → `SymmetricalCrossSection`,
   otherwise `AsymmetricalCrossSection`. A lone section at a non-zero offset does break the
   profile's mirror symmetry, so it lands here.
2. *For a cross section derived from a single section* (B8 — the port case): offset is
   irrelevant. A single strip is always mirror-symmetric about its own center, so recenter
   it and put the offset on the port's transform. It is asymmetric only when the span is
   **odd**, because then the center falls between grid points and there is no on-grid
   position for the port.

Verified today, no change needed: `width=0.451 µm` → `section_min=-225, section_max=226`
registers, extrudes, writes and reads back equal (`width` 451, same name). The only thing
to document is that a nominally "symmetric" gdsfactory waveguide with an odd-nm width is an
asymmetric cross section here, so `connect()` applies the asymmetric mirror rules to it.

### 4. Registration and naming

**One structure, one name — no aliases.** `_register` keeps rejecting a second explicit
name for an existing structure. The consequence is gdsfactory-side: `metal_routing` must
become an alias *of* `metal3` at the factory level (`metal_routing = metal3`, one name
wins) rather than a second function producing an identical profile under its own name.
Callers asking for `"metal_routing"` then get a cross section named `metal3`, which is the
point — the name identifies the structure. The `import_gds.py:58` workaround is deleted,
not generalised.

**Radius stays non-identifying**, which is kfactory's current behaviour — worth stating
explicitly because it is easy to assume the opposite: `__eq__` compares only
width/enclosure/name and carries the comment *"radius/radius_min are non-identifying
metadata"* (`cross_section.py:173`), `__hash__` excludes them, `_asym_auto_name` documents
*"excluding radius"* (`cross_section.py:303`), and `_resolve_radius` (`cross_section.py:324`)
exists precisely to raise when the same structure is re-registered with a different one.

Combined with no-aliases, this is a real constraint on gdsfactory and should be agreed
before implementation: **a PDK cannot hold two cross sections that differ only in default
bend radius.** `strip(radius=5)` and `strip(radius=10)` are one structure; the second
registration raises rather than producing a second profile. gdsfactory does this in three
places today (`disk.py:128`, `coupler_bent.py:41-42`) plus three `get_cross_section(...,
radius=…)` call sites, all of which must instead pass the radius to the bend/route call —
which is exactly what `_resolve_radius`'s error message already tells you to do.

Two presets dissolve on their own under this model rather than needing a decision:
`strip_no_ports` exists only to carry `port_names=("", "")`, and port information is no
longer part of a cross section, so it stops being a distinct profile at all.

### 5. Serialization

Unchanged in shape — symmetric entries keep referencing their enclosure by name, asymmetric
entries keep writing their strips. The only fix is B6: `LayerEnclosure`'s
`@model_serializer` must emit `bbox_sections`, and `__eq__`/`__hash__` must agree on
whether they count. Keep omitting `None`/default fields so files don't bloat. No format
version bump needed, since nothing about the layout of the metadata changes.

### 6. What `gf.cross_section()` builds

No bridge type, no `to_/from_gdsfactory` helpers — the factory constructs the kfactory
object directly and returns it. The field mapping it applies:

| gdsfactory                        | kfactory                                              |
|-----------------------------------|-------------------------------------------------------|
| mirror-symmetric profile          | `SymmetricalCrossSection`: `sections[0]` → `width` + `main_layer`; other sections → enclosure bands **relative to the core edge** |
| anything else                     | `AsymmetricalCrossSection`: `sections[0]` → main strip, rest → absolute `sections` |
| `Section.width`, `Section.offset` | edges rounded to dbu individually (§3), then made relative or absolute per the two rows above |
| `Section.layer`                   | `layer`                                                |
| `radius`, `radius_min`            | `radius`, `radius_min` (dbu)                           |
| `bbox_layers` + `bbox_offsets`    | `bbox_sections`                                        |
| `CrossSection.name`               | `name` (stored verbatim)                               |
| `Section.name` / `port_names` / `port_types` / `hidden` / `simplify` / `insets` | **not stored** — extruder arguments (§1) |

Converting a symmetric profile's cladding to edge-relative bands is where gdsfactory's
absolute offsets get reinterpreted, and it is deliberate: from then on `copy(width=…)`
scales the cladding with the core.

## Phasing

kfactory:

- **P0 (independent bugfix):** `bbox_sections` serialization + `__eq__`/`__hash__`
  consistency, with a regression test. Ships on its own, unrelated to gdsfactory.
- **P1:** add `get_sections()` on both types (§2); optionally the section→cross-section
  helper for ports (B8). Additive.
- **P2:** document the µm→dbu rule, the two symmetric/asymmetric decisions (§3) and
  name stability (B9).

gdsfactory, once P1 is available:

- **P3:** `gf.cross_section()` returns the kfactory type; `gf.CrossSection`/`Section`
  deleted; `add_bbox`/`validate_radius` become free functions; `.sections` call sites move
  to `get_sections()`.
- **P4:** move `width_function` to an `extrude()` argument in the four components that use
  it; radius overrides to the bend/route call; canonicalise `metal_routing`; delete the
  `import_gds.py` workaround.

## Acceptance criteria

1. For every cross section in `gdsfactory.cross_section.cross_sections` (30) plus a
   handcrafted set covering odd-nm widths (→ asymmetric), nested same-layer sections and
   bbox layers: `gf.cross_section(...) → write → read` yields a kfactory cross section
   equal to the one written — same ordered sections, name, radius/radius_min and bbox.
2. Component-level: `p.extrude(xs)` → write → read gives back the same shapes *and* the
   same ports (names, types, widths, positions, and each port's cross section). This is
   where the port set is guaranteed, not via the profile.
3. Collapsing stays lossless where it matters: a core with a same-layer trench or slab
   keeps its `width`/main strip through normalization, and `get_sections()` on a symmetric
   cross section returns cladding resolved against the core width (±3.25 µm at a 500 nm
   core, ±3.55 µm at 1100 nm for a 3 µm band).
4. kfactory-only: `xs == read_back(xs)` for all fields including `bbox_sections`, for both
   symmetric and asymmetric cross sections.
5. `metal_routing` resolves to the same cross section object as `metal3`, named `metal3`,
   and registering both raises nothing; the `import_gds.py:58` workaround in gdsfactory is
   deleted rather than generalised.
6. Existing oas regression goldens are either unchanged or regenerated with a documented,
   geometry-verified diff.

## Open question

One item is a gdsfactory API change rather than a kfactory design choice, so it should be
confirmed before the port starts. No aliases (§4) *and* non-identifying radius (§4)
together mean **a PDK cannot hold two cross sections differing only in default bend
radius**: `strip(radius=5)` and `strip(radius=10)` are one structure, and the second
registration raises. gdsfactory relies on this in five places today (`disk.py:128`,
`coupler_bent.py:41-42`, plus three `get_cross_section(..., radius=…)` sites), all of which
must pass the radius to the bend/route call instead — which is what `_resolve_radius`'s
error message already instructs. Mechanical, but it is a visible API change.
