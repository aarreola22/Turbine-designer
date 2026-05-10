"""
3D runner geometry for the Crossflow (Banki-Michell) turbine.

Uses CadQuery (wraps OpenCASCADE) to produce a parametric solid model
that can be exported as STEP (SolidWorks / Fusion 360) or STL (Blender / 3D print).

All lengths are in metres internally; CadQuery works in mm, so all values
are scaled ×1000 before being passed to CadQuery.
"""

import math
from pathlib import Path

try:
    import cadquery as cq
    HAS_CQ = True
except ImportError:
    HAS_CQ = False


def _require_cadquery():
    if not HAS_CQ:
        raise ImportError(
            "CadQuery is not installed.\n"
            "Install it with:  pip install cadquery\n"
            "or see https://cadquery.readthedocs.io/en/latest/installation.html"
        )


# ── Low-level arc helpers ────────────────────────────────────────────────────

def _blade_arc_points(R1_m: float, R2_m: float, rho_b_m: float,
                       beta1_deg: float, delta_deg: float,
                       n_pts: int = 40) -> list[tuple[float, float]]:
    """
    Return polyline approximation of one blade arc in the X-Y plane (mm).

    Convention (matches Quaranta 2022):
      • Reference blade outer tip at (R1, 0) in runner frame.
      • Arc centre at (R1 - ρb·cos β1,  -ρb·sin β1).
      • Arc sweeps from angle (π - β1) to (π - β1 + δ) measured from centre.
    """
    R1   = R1_m   * 1000   # → mm
    rho  = rho_b_m * 1000

    beta1 = math.radians(beta1_deg)
    delta = math.radians(delta_deg)

    # Arc centre relative to runner axis
    cx = (R1_m - rho_b_m * math.cos(beta1)) * 1000
    cy = (-rho_b_m * math.sin(beta1)) * 1000

    # Starting angle: arc centre → outer tip = (R1_mm, 0)
    start_ang = math.atan2(0 - cy, R1 - cx)

    pts = []
    for i in range(n_pts + 1):
        t   = i / n_pts
        ang = start_ang + t * delta   # sweep from outer tip toward inner tip
        x   = cx + rho * math.cos(ang)
        y   = cy + rho * math.sin(ang)
        pts.append((x, y))
    return pts


def _rotate_pts(pts: list[tuple[float, float]],
                angle_rad: float) -> list[tuple[float, float]]:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


# ── Main builder ─────────────────────────────────────────────────────────────

def build_runner(params: dict,
                 blade_thickness_mm: float = 3.0,
                 shaft_radius_mm:    float = 20.0,
                 disc_thickness_mm:  float = 8.0) -> "cq.Workplane":
    """
    Build the complete runner solid.

    Parameters
    ----------
    params              : dict returned by calculator.design()
    blade_thickness_mm  : radial thickness of each blade, mm
    shaft_radius_mm     : radius of the central shaft bore, mm
    disc_thickness_mm   : thickness of each end disc, mm

    Returns
    -------
    CadQuery Workplane containing the assembled runner solid.
    """
    _require_cadquery()

    R1_mm  = params["R1_m"]  * 1000
    R2_mm  = params["R2_m"]  * 1000
    B_mm   = params["B_m"]   * 1000
    rho_mm = params["rho_b_m"] * 1000
    Nb     = params["Nb"]
    beta1  = params["beta1_deg"]
    delta  = params["delta_deg"]

    blade_half = blade_thickness_mm / 2.0
    total_length = B_mm + 2 * disc_thickness_mm   # full axial length

    # ── Reference blade arc (outer tip at (R1, 0)) ──────────────────────────
    arc_pts = _blade_arc_points(
        params["R1_m"], params["R2_m"], params["rho_b_m"],
        beta1, delta
    )

    # Build offset polygon: walk pts forward by blade_half, back by blade_half
    # Simple normal-offset using perpendicular to each segment
    def offset_arc(pts, offset):
        result = []
        n = len(pts)
        for i in range(n):
            if i == 0:
                dx = pts[1][0] - pts[0][0]
                dy = pts[1][1] - pts[0][1]
            elif i == n - 1:
                dx = pts[-1][0] - pts[-2][0]
                dy = pts[-1][1] - pts[-2][1]
            else:
                dx = pts[i+1][0] - pts[i-1][0]
                dy = pts[i+1][1] - pts[i-1][1]
            length = math.hypot(dx, dy)
            nx, ny = -dy / length, dx / length   # left normal
            result.append((pts[i][0] + nx * offset, pts[i][1] + ny * offset))
        return result

    front_pts = offset_arc(arc_pts,  blade_half)
    back_pts  = offset_arc(arc_pts, -blade_half)
    # Closed polygon: front forward, back reversed
    profile_2d = front_pts + back_pts[::-1]

    # ── Build all blades ─────────────────────────────────────────────────────
    angle_step = 2 * math.pi / Nb

    blade_solid = None
    for i in range(Nb):
        rotated = _rotate_pts(profile_2d, i * angle_step)
        wire = (
            cq.Workplane("XY")
            .polyline([(x, y) for x, y in rotated])
            .close()
        )
        blade_i = wire.extrude(B_mm)
        # Translate blades to sit between the two discs (z centred)
        blade_i = blade_i.translate((0, 0, disc_thickness_mm))

        if blade_solid is None:
            blade_solid = blade_i
        else:
            blade_solid = blade_solid.union(blade_i)

    # ── End discs (annular rings) ─────────────────────────────────────────────
    def make_disc(z_offset):
        outer = cq.Workplane("XY").workplane(offset=z_offset).circle(R1_mm)
        disc  = outer.extrude(disc_thickness_mm)
        # Cut inner bore
        disc  = disc.faces(">Z").workplane().circle(shaft_radius_mm).cutBlind(-disc_thickness_mm)
        return disc

    disc_bottom = make_disc(0)
    disc_top    = make_disc(disc_thickness_mm + B_mm)

    # ── Central shaft ─────────────────────────────────────────────────────────
    shaft = (
        cq.Workplane("XY")
        .circle(shaft_radius_mm)
        .extrude(total_length)
    )

    # ── Assemble ─────────────────────────────────────────────────────────────
    runner = shaft
    if blade_solid is not None:
        runner = runner.union(blade_solid)
    runner = runner.union(disc_bottom).union(disc_top)

    return runner


# ── Export helpers ────────────────────────────────────────────────────────────

def export_step(shape: "cq.Workplane", filepath: str | Path) -> None:
    """Export runner as STEP file (SolidWorks / Fusion 360 compatible)."""
    _require_cadquery()
    cq.exporters.export(shape, str(filepath), cq.exporters.ExportTypes.STEP)
    print(f"  STEP file written → {filepath}")


def export_stl(shape: "cq.Workplane", filepath: str | Path,
               tolerance: float = 0.01, angular_tolerance: float = 0.1) -> None:
    """Export runner as binary STL file (Blender / 3D-print ready)."""
    _require_cadquery()
    cq.exporters.export(
        shape, str(filepath), cq.exporters.ExportTypes.STL,
        tolerance=tolerance, angularTolerance=angular_tolerance
    )
    print(f"  STL file written  → {filepath}")


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    from calculator import design

    params = design(H=10.0, Q=0.5)
    print(f"Building runner: D1={params['D1_m']*1000:.0f} mm, "
          f"D2={params['D2_m']*1000:.0f} mm, "
          f"B={params['B_m']*1000:.0f} mm, "
          f"Nb={params['Nb']}")

    runner = build_runner(params)

    out = Path(__file__).parent / "output"
    out.mkdir(exist_ok=True)
    export_step(runner, out / "runner.step")
    export_stl(runner,  out / "runner.stl")
    print("Done.")
