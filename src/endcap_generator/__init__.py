"""CLI entry point: generate an STL/OBJ end cap for a rectangular steel profile.

Example:
    uv run endcap-generator --outer-x 40 --outer-y 40 --wall-thickness 2 \\
        --rib-gap 6 --rib-height 0.5 -o my_cap
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cadquery as cq

from .geometry import EndCapParams, build_end_cap


def _export_stl(model: cq.Workplane, path: Path) -> None:
    cq.exporters.export(model, str(path), tolerance=0.05, angularTolerance=0.1)


def _export_obj(stl_path: Path, obj_path: Path) -> None:
    """CadQuery has no native OBJ exporter, so re-tessellate the STL via trimesh."""
    import trimesh

    mesh = trimesh.load_mesh(str(stl_path))
    mesh.export(str(obj_path))


def _fmt_dim(value: float) -> str:
    """Format a dimension without a trailing '.0' for whole numbers (e.g. 40, 12.5)."""
    return f"{value:g}"


def default_output_path(p: EndCapParams) -> Path:
    """cap_<outer-x>x<outer-y>, with a _lip suffix if the lip sleeves beyond the profile."""
    name = f"cap_{_fmt_dim(p.outer_x)}x{_fmt_dim(p.outer_y)}"
    if p.has_lip:
        name += "_lip"
    return Path(name)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a 3D-printable end cap for a rectangular steel profile."
    )
    parser.add_argument("--outer-x", type=float, required=True, help="Outer profile width X (mm)")
    parser.add_argument("--outer-y", type=float, required=True, help="Outer profile width Y (mm)")
    parser.add_argument("--wall-thickness", type=float, required=True, help="Profile wall thickness (mm)")

    parser.add_argument("--corner-radius", type=float, default=3.0, help="Outer corner radius (mm)")
    parser.add_argument("--cap-thickness", type=float, default=2.5, help="Top plate thickness (mm)")
    parser.add_argument("--lip-height", type=float, default=8.0, help="Outer skirt/lip height (mm); <= 0 disables the lip so the top plate stays flush with the profile")
    parser.add_argument("--lip-thickness", type=float, default=None, help="Lip wall thickness (mm, default = wall-thickness)")
    parser.add_argument("--lip-clearance", type=float, default=0.3, help="Per-side slide-fit gap between the tube's outer surface and the lip pocket (mm)")
    parser.add_argument("--insert-depth", type=float, default=10.0, help="Ribbed plug depth (mm)")
    parser.add_argument("--insert-clearance", type=float, default=0.3, help="Per-side clearance before ribs (mm)")
    parser.add_argument("--insert-wall-thickness", type=float, default=2.0, help="Hollow plug shell thickness, lets ribs flex inward (mm)")
    parser.add_argument("--rib-count", type=int, default=None, help="Explicit number of ribs per face (overrides --rib-gap)")
    parser.add_argument("--rib-gap", type=float, default=8.0, help="Target spacing between ribs (mm)")
    parser.add_argument("--rib-height", type=float, default=0.6, help="Rib protrusion / interference (mm)")
    parser.add_argument("--rib-width", type=float, default=1.0, help="Rib thickness (mm)")
    parser.add_argument("--lead-in", type=float, default=1.0, help="Rib-free tapered entry length at plug tip (mm)")

    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output file path without extension (default: auto-generated as cap_<x>x<y>[_lip])",
    )
    parser.add_argument(
        "--format", choices=["stl", "obj", "both"], default="both",
        help="Which file format(s) to export (default: both)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        params = EndCapParams(
            outer_x=args.outer_x,
            outer_y=args.outer_y,
            wall_thickness=args.wall_thickness,
            corner_radius=args.corner_radius,
            cap_thickness=args.cap_thickness,
            lip_height=args.lip_height,
            lip_thickness=args.lip_thickness,
            lip_clearance=args.lip_clearance,
            insert_depth=args.insert_depth,
            insert_clearance=args.insert_clearance,
            insert_wall_thickness=args.insert_wall_thickness,
            rib_count=args.rib_count,
            rib_gap=args.rib_gap,
            rib_height=args.rib_height,
            rib_width=args.rib_width,
            lead_in=args.lead_in,
        )
    except ValueError as exc:
        print(f"Invalid parameters: {exc}", file=sys.stderr)
        return 1

    model = build_end_cap(params)

    out_base = args.output if args.output is not None else default_output_path(params)
    out_base.parent.mkdir(parents=True, exist_ok=True)

    stl_path = out_base.with_suffix(".stl")
    if args.format in ("stl", "both"):
        _export_stl(model, stl_path)
        print(f"Wrote {stl_path}")

    if args.format in ("obj", "both"):
        if args.format == "obj" and not stl_path.exists():
            _export_stl(model, stl_path)
        obj_path = out_base.with_suffix(".obj")
        _export_obj(stl_path, obj_path)
        print(f"Wrote {obj_path}")
        if args.format == "obj":
            stl_path.unlink(missing_ok=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
