# End Cap Generator

Parametric STL/OBJ generator for a rectangular steel-profile end cap, built with
[CadQuery](https://cadquery.readthedocs.io/). The cap has a flat top plate sized
to seal over the tube's end, an outer skirt/lip that sleeves down over the
outside of the profile's walls (to keep water from seeping in at the seam),
and a ribbed inner plug that friction-fits inside the tube.

## Setup

```bash
uv sync
```

## Usage

```bash
uv run endcap-generator --outer-x 40 --outer-y 40 --wall-thickness 2
```

This writes an auto-named `cap_40x40_lip.stl` / `cap_40x40_lip.obj` in the current
directory (the `_lip` suffix is added whenever the skirt sleeves out beyond the
profile's outer dimensions). Pass `-o out/cap` to use an explicit path instead.

### Required parameters

| Flag | Description |
|---|---|
| `--outer-x` | Outer profile width X (mm) |
| `--outer-y` | Outer profile width Y (mm) |
| `--wall-thickness` | Steel profile wall thickness (mm) |

### Optional parameters

| Flag | Default | Description |
|---|---|---|
| `--corner-radius` | 3.0 | Outer corner radius of the profile (mm) |
| `--cap-thickness` | 2.5 | Top plate thickness (mm) |
| `--lip-height` | 8.0 | Height of the outer skirt covering the profile's outside walls (mm) |
| `--lip-thickness` | = wall-thickness | Skirt wall thickness (mm) |
| `--lip-clearance` | 0.3 | Per-side slide-fit gap between the tube's outer surface and the lip pocket (mm) |
| `--insert-depth` | 10.0 | How far the ribbed plug goes into the tube (mm) |
| `--insert-clearance` | 0.3 | Per-side gap between plug body and inner cavity before ribs (mm) |
| `--rib-count` | auto | Explicit ribs per face (overrides `--rib-gap`) |
| `--rib-gap` | 8.0 | Target spacing between ribs (mm) |
| `--rib-height` | 0.6 | How far each rib protrudes / interferes with the tube wall (mm) |
| `--rib-width` | 1.0 | Rib thickness (mm) |
| `--lead-in` | 1.0 | Rib-free tapered length at the plug tip, to ease insertion (mm) |
| `-o`, `--output` | auto: `cap_<x>x<y>[_lip]` | Output path without extension |
| `--format` | `both` | `stl`, `obj`, or `both` |

## Tuning for your printer/material

- `--rib-height` controls interference fit strength. Start around 0.4–0.6 mm
  for PLA/PETG; increase slightly for a tighter grip, decrease if the cap
  won't seat fully.
- `--insert-clearance` should roughly match your printer's dimensional
  accuracy (0.2–0.4 mm is a good start) so the plug body itself slides in
  freely and only the ribs provide friction.
- `--lip-clearance` is the same kind of fit tolerance, but for the outer
  skirt sliding over the tube; 0.2–0.4 mm is a good starting point. Note the
  cap's overall footprint grows by `2 * (lip_clearance + lip_thickness)` in
  each dimension, since the top plate is sized to seal the whole skirt.
- If your profile has sharp (non-rounded) outer corners, set
  `--corner-radius 0`.

## Project layout

- `src/endcap_generator/geometry.py` — parametric solid model (`EndCapParams`, `build_end_cap`)
- `src/endcap_generator/__init__.py` — CLI / STL & OBJ export
