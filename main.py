"""
Crossflow turbine calculator — command-line entry point.

Usage examples:
  python main.py --head 10 --flow 0.5
  python main.py --head 15 --flow 1.2 --eta 0.82 --export-step --export-stl
  python main.py --head 5 --flow 0.3 --output-dir ./my_project
"""

import argparse
import sys
from pathlib import Path

from calculator import design, print_summary


def parse_args():
    p = argparse.ArgumentParser(
        description="Crossflow (Banki-Michell) hydro turbine design calculator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Required site parameters
    p.add_argument("--head", "-H", type=float, required=True,
                   metavar="METERS",
                   help="Gross hydraulic head at the site, in metres")
    p.add_argument("--flow", "-Q", type=float, required=True,
                   metavar="M3_PER_S",
                   help="Design flow rate, in m³/s")

    # Optional tuning
    p.add_argument("--eta", type=float, default=0.80,
                   metavar="EFFICIENCY",
                   help="Expected overall efficiency (0–1, default 0.80)")
    p.add_argument("--alpha", type=float, default=16.0,
                   metavar="DEGREES",
                   help="Nozzle jet angle in degrees (default 16°, optimal)")
    p.add_argument("--nozzle-arc", type=float, default=30.0,
                   metavar="DEGREES",
                   help="Nozzle throat opening arc in degrees (default 30°; smaller = wider runner)")

    # Geometry export
    p.add_argument("--export-step", action="store_true",
                   help="Export 3D runner geometry as STEP (SolidWorks/Fusion 360)")
    p.add_argument("--export-stl", action="store_true",
                   help="Export 3D runner geometry as STL (Blender/3D print)")
    p.add_argument("--output-dir", type=Path, default=Path("."),
                   metavar="DIR",
                   help="Directory for exported files (default: current directory)")

    # Blade geometry overrides
    p.add_argument("--blade-thickness", type=float, default=3.0,
                   metavar="MM",
                   help="Blade thickness, mm (default 3.0)")
    p.add_argument("--shaft-radius", type=float, default=20.0,
                   metavar="MM",
                   help="Shaft radius, mm (default 20.0)")

    return p.parse_args()


def validate(args):
    errors = []
    if args.head <= 0:
        errors.append("--head must be positive")
    if args.flow <= 0:
        errors.append("--flow must be positive")
    if not (0.0 < args.eta <= 1.0):
        errors.append("--eta must be between 0 and 1 (exclusive)")
    if not (5.0 <= args.alpha <= 40.0):
        errors.append("--alpha should be between 5° and 40° (typical range)")
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    args = parse_args()
    validate(args)

    # ── Hydraulic design ──────────────────────────────────────────────────────
    params = design(
        H=args.head,
        Q=args.flow,
        eta_assumed=args.eta,
        alpha_deg=args.alpha,
        nozzle_arc_deg=args.nozzle_arc,
    )
    print_summary(params)

    # ── 3D geometry export ────────────────────────────────────────────────────
    if args.export_step or args.export_stl:
        try:
            from geometry import build_runner, export_step, export_stl
        except ImportError as exc:
            print(f"Cannot load geometry module: {exc}", file=sys.stderr)
            sys.exit(1)

        args.output_dir.mkdir(parents=True, exist_ok=True)

        print("  Building 3D runner geometry …")
        try:
            runner = build_runner(
                params,
                blade_thickness_mm=args.blade_thickness,
                shaft_radius_mm=args.shaft_radius,
            )
        except ImportError as exc:
            # CadQuery not installed
            print(f"\n  {exc}", file=sys.stderr)
            sys.exit(1)

        if args.export_step:
            export_step(runner, args.output_dir / "runner.step")
        if args.export_stl:
            export_stl(runner, args.output_dir / "runner.stl")

        print(f"\n  Files written to: {args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
