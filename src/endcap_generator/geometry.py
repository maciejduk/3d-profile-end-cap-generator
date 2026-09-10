"""Parametric geometry for a steel-profile end cap.

The cap consists of three stacked features:
  1. Top plate  - flat rectangle that sits on top of the profile.
  2. Outer lip  - thin skirt hanging down around the plate. Its pocket wraps
                  around the OUTSIDE of the profile (with a small slide
                  clearance), so the top plate seals over the tube's end and
                  water can't seep in at the cap/profile seam.
  3. Inner plug - hollow, ribbed insert that goes inside the profile's
                  cavity. Being hollow lets its shell walls flex slightly
                  under the ribs, so they squeeze inward and grip the tube.
"""

from __future__ import annotations

from dataclasses import dataclass

import cadquery as cq


@dataclass
class EndCapParams:
    # Required - outer dimensions of the steel profile (mm).
    outer_x: float
    outer_y: float
    wall_thickness: float

    # Optional geometry tweaks (all in mm unless noted).
    corner_radius: float = 3.0          # outer corner rounding of the profile
    cap_thickness: float = 2.5          # thickness of the flat top plate
    lip_height: float = 8.0             # how far the outer skirt covers the walls
    lip_thickness: float | None = None  # skirt wall thickness (defaults to wall_thickness)
    lip_clearance: float = 0.3          # per-side slide-fit gap between the tube's outer surface and the lip pocket
    insert_depth: float = 10.0          # how deep the ribbed plug goes into the tube
    insert_clearance: float = 0.3       # gap per side between plug body and inner cavity
    insert_wall_thickness: float = 2.0  # shell thickness of the hollow plug (lets ribs flex inward)
    rib_count: int | None = None        # explicit rib count per side (overrides rib_gap)
    rib_gap: float = 8.0                # target spacing between ribs when rib_count is None
    rib_height: float = 0.6             # how far a rib protrudes beyond the plug body
    rib_width: float = 1.0              # thickness of each rib
    lead_in: float = 1.0                # tapered, rib-free entry length at the plug tip

    def __post_init__(self) -> None:
        if self.lip_thickness is None:
            self.lip_thickness = self.wall_thickness

        if self.outer_x <= 0 or self.outer_y <= 0:
            raise ValueError("outer_x and outer_y must be positive")
        if self.wall_thickness <= 0:
            raise ValueError("wall_thickness must be positive")
        if self.corner_radius < 0:
            raise ValueError("corner_radius must be >= 0")
        max_radius = min(self.outer_x, self.outer_y) / 2
        if self.corner_radius >= max_radius:
            raise ValueError(
                f"corner_radius must be < {max_radius:.2f} for a {self.outer_x}x{self.outer_y} profile"
            )

        inner_x = self.outer_x - 2 * self.wall_thickness
        inner_y = self.outer_y - 2 * self.wall_thickness
        if inner_x <= 0 or inner_y <= 0:
            raise ValueError("wall_thickness is too large for the given outer dimensions")

        if self.lip_thickness <= 0:
            raise ValueError("lip_thickness must be positive")
        if self.lip_clearance < 0:
            raise ValueError("lip_clearance must be >= 0")

        plug_x = inner_x - 2 * self.insert_clearance
        plug_y = inner_y - 2 * self.insert_clearance
        if plug_x <= 0 or plug_y <= 0:
            raise ValueError("insert_clearance is too large for the given wall_thickness")
        if self.insert_wall_thickness <= 0:
            raise ValueError("insert_wall_thickness must be positive")
        if self.insert_wall_thickness * 2 >= min(plug_x, plug_y):
            raise ValueError("insert_wall_thickness is too large for the resulting plug size")

    @property
    def inner_x(self) -> float:
        """Nominal inner cavity size (X) of the steel profile."""
        return self.outer_x - 2 * self.wall_thickness

    @property
    def inner_y(self) -> float:
        """Nominal inner cavity size (Y) of the steel profile."""
        return self.outer_y - 2 * self.wall_thickness

    @property
    def inner_corner_radius(self) -> float:
        return max(self.corner_radius - self.wall_thickness, 0.0)

    @property
    def lip_pocket_x(self) -> float:
        """Inner size (X) of the lip pocket - just larger than the tube's outer X for a slide fit."""
        return self.outer_x + 2 * self.lip_clearance

    @property
    def lip_pocket_y(self) -> float:
        """Inner size (Y) of the lip pocket - just larger than the tube's outer Y for a slide fit."""
        return self.outer_y + 2 * self.lip_clearance

    @property
    def lip_pocket_radius(self) -> float:
        return self.corner_radius + self.lip_clearance

    @property
    def lip_outer_x(self) -> float:
        """Overall footprint (X) of the cap: lip pocket plus the skirt's own wall."""
        return self.lip_pocket_x + 2 * self.lip_thickness

    @property
    def lip_outer_y(self) -> float:
        """Overall footprint (Y) of the cap: lip pocket plus the skirt's own wall."""
        return self.lip_pocket_y + 2 * self.lip_thickness

    @property
    def lip_outer_radius(self) -> float:
        return self.lip_pocket_radius + self.lip_thickness


def _rounded_rect_solid(x: float, y: float, radius: float, height: float) -> cq.Workplane:
    """A box extruded from a (possibly corner-rounded) rectangle, height can be negative."""
    solid = cq.Workplane("XY").rect(x, y).extrude(height)
    if radius > 0:
        solid = solid.edges("|Z").fillet(radius)
    return solid


def build_end_cap(p: EndCapParams) -> cq.Workplane:
    """Return a single solid (CadQuery Workplane) representing the end cap.

    Coordinate system: Z=0 is the underside of the top plate (the face that
    rests on the profile's end). The top plate extends upward (+Z), the lip
    and the ribbed plug both extend downward (-Z) from Z=0.

    The top plate and lip are both sized to the cap's full outer footprint
    (tube outer dims + lip_clearance + lip_thickness on each side), so the
    plate fully seals over the tube's end - the lip's pocket then slides
    down over the tube's actual outside surface.
    """
    top_plate = _rounded_rect_solid(p.lip_outer_x, p.lip_outer_y, p.lip_outer_radius, p.cap_thickness)

    lip_outer = _rounded_rect_solid(p.lip_outer_x, p.lip_outer_y, p.lip_outer_radius, -p.lip_height)
    lip_pocket = _rounded_rect_solid(p.lip_pocket_x, p.lip_pocket_y, p.lip_pocket_radius, -p.lip_height)
    lip = lip_outer.cut(lip_pocket)

    plug = _build_plug(p)

    cap = top_plate.union(lip).union(plug)
    return cap


def _build_plug(p: EndCapParams) -> cq.Workplane:
    """Hollow, ribbed insert that friction-fits inside the profile's cavity.

    The plug is a thin-walled shell (wall = insert_wall_thickness) open at
    both ends, rather than a solid block, so the ribbed walls can flex
    inward slightly as the cap is pushed in - that spring-back is what
    generates the squeeze/friction holding the cap in place.
    """
    plug_x = p.inner_x - 2 * p.insert_clearance
    plug_y = p.inner_y - 2 * p.insert_clearance
    outer = _rounded_rect_solid(plug_x, plug_y, p.inner_corner_radius, -p.insert_depth)

    cavity_x = plug_x - 2 * p.insert_wall_thickness
    cavity_y = plug_y - 2 * p.insert_wall_thickness
    cavity_radius = max(p.inner_corner_radius - p.insert_wall_thickness, 0.0)
    cavity = _rounded_rect_solid(cavity_x, cavity_y, cavity_radius, -p.insert_depth)
    body = outer.cut(cavity)

    if p.rib_height <= 0:
        return body

    straight_height = max(p.insert_depth - p.lead_in, 0.0)
    taper_height = p.insert_depth - straight_height
    ribs = _build_ribs(p, plug_x, plug_y, straight_height, taper_height)
    if ribs is None:
        return body

    plug = body.union(ribs)
    return plug


def _build_ribs(
    p: EndCapParams, plug_x: float, plug_y: float, straight_height: float, taper_height: float
) -> cq.Workplane | None:
    """Build friction ribs along each of the 4 outer faces of the plug.

    Each rib is a straight prism for `straight_height` (near the cap) then
    tapers down to nearly flush over `taper_height` (near the tip), so the
    insert has a gentle lead-in instead of an abrupt rib edge.
    """
    half_x, half_y = plug_x / 2, plug_y / 2
    rib_solids: list[cq.Workplane] = []

    for length, half_extent, axis in ((plug_x, half_y, "y"), (plug_y, half_x, "x")):
        positions = _rib_positions(length, p.rib_gap, p.rib_count)
        for pos in positions:
            for side in (1, -1):
                rib = _tapered_rib(
                    axis=axis,
                    pos=pos,
                    side=side,
                    half_extent=half_extent,
                    rib_height=p.rib_height,
                    rib_width=p.rib_width,
                    straight_height=straight_height,
                    taper_height=taper_height,
                )
                rib_solids.append(rib)

    if not rib_solids:
        return None

    ribs = rib_solids[0]
    for r in rib_solids[1:]:
        ribs = ribs.union(r)
    return ribs


def _tapered_rib(
    *,
    axis: str,
    pos: float,
    side: int,
    half_extent: float,
    rib_height: float,
    rib_width: float,
    straight_height: float,
    taper_height: float,
) -> cq.Workplane:
    """A single rib solid: protrudes by `rib_height` for `straight_height`,
    then tapers (via loft) down to a near-flush tip over `taper_height`.

    `axis` is which axis the rib protrudes along ("x" faces protrude in X,
    "y" faces protrude in Y); `pos` is the fixed position along the other axis.
    """
    tip_protrusion = min(max(rib_height * 0.08, 0.05), rib_height)

    def _add_profile(wp: cq.Workplane, protrusion: float) -> cq.Workplane:
        if axis == "x":
            cx = side * (half_extent + protrusion / 2)
            return wp.moveTo(cx, pos).rect(protrusion, rib_width)
        cy = side * (half_extent + protrusion / 2)
        return wp.moveTo(pos, cy).rect(rib_width, protrusion)

    wp = _add_profile(cq.Workplane("XY"), rib_height)
    if straight_height > 1e-6:
        wp = _add_profile(wp.workplane(offset=-straight_height), rib_height)
    if taper_height > 1e-6:
        wp = _add_profile(wp.workplane(offset=-taper_height), tip_protrusion)
    return wp.loft(ruled=True)


def _rib_positions(face_length: float, rib_gap: float, rib_count: int | None) -> list[float]:
    """Evenly spaced rib center positions along one axis, inset from the corners."""
    margin = face_length * 0.12  # keep ribs away from rounded corners
    usable = face_length - 2 * margin
    if usable <= 0:
        return [0.0]

    if rib_count is None:
        rib_count = max(int(usable // rib_gap) + 1, 1)
    rib_count = max(rib_count, 1)

    if rib_count == 1:
        return [0.0]

    step = usable / (rib_count - 1)
    start = -usable / 2
    return [start + i * step for i in range(rib_count)]
