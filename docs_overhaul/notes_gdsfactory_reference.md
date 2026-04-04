# gdsfactory Documentation — Reference Analysis

## What makes gdsfactory docs good (and what to replicate)

### Structure
- Clear hierarchy: Getting Started -> Layout Fundamentals -> Advanced -> API Reference
- Dedicated page for each core concept (not bundled into omnibus tutorials)
- Each concept page has: explanation, code example, visual output, links to related concepts

### Sections they have that kfactory lacks
| gdsfactory section | kfactory equivalent needed |
|---|---|
| Components (with visual gallery) | `components/overview.py` |
| Instances & Ports (dedicated) | `concepts/ports.py`, `concepts/instances.py` |
| Path & CrossSection | `enclosures/cross_sections.py` |
| Routing (with 15+ function refs) | `routing/*.py` (entire section) |
| Grid & Packing | `utilities/grid.py`, `utilities/packing.py` |
| Die Assembly | could be part of `utilities/grid.py` or `pdk/creating_pdk.py` |
| Best Practices | `howto/best_practices.py` |
| Contributing | not prioritized but nice to have |
| PDK (3 dedicated pages) | `pdk/creating_pdk.py`, `pdk/technology.py` |
| Training materials / courses | out of scope for now |

### Quality patterns to follow
1. **Every concept page shows visual output** — don't just explain, show the rendered layout
2. **Progressive disclosure** — start simple, layer complexity
3. **Cross-linking** — each page links to related pages ("see also: Routing, Cross-Sections")
4. **Consistent structure per page**: brief intro -> imports/setup -> explanation with code -> summary/next steps
5. **API functions shown in context** — not just signatures, but "here's when and why you'd use this"

### What kfactory already does better than gdsfactory docs
- YAML serialization (bidirectional hierarchical conversion)
- KLayout integration (native backend, not gdspy)
- Minkowski sum operations for enclosures
- Integer grid snapping by default (no float precision issues)

These are differentiators worth highlighting in the docs.
