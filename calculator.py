"""
Crossflow (Banki-Michell) hydro turbine design calculator.

Primary reference: Quaranta et al. (2022) — dimensionless design methodology.
Secondary references: Sammartano (2013) nozzle geometry, Mockmore (1949) blade count.
"""

import math


# ── Physical constants ──────────────────────────────────────────────────────
G = 9.81  # gravitational acceleration, m/s²


# ── Design constants from Quaranta 2022 ────────────────────────────────────
CV        = 0.98    # nozzle velocity coefficient
ALPHA_DEG = 16.0    # nozzle jet angle from tangent (optimal), degrees
SR_OPT    = 0.565   # optimal speed ratio u1/V
D_RATIO   = 0.665   # D2/D1 inner-to-outer diameter ratio
B_RATIO   = 1.5     # runner width / nozzle width
ETA_HYD   = 0.94    # hydraulic efficiency factor (Hn = eta_hyd * H)
LAMBDA    = 0.087   # nozzle arc fraction (default ~5° → 2π×5/360 ≈ 0.087 rad equivalent fraction)
                    # More precisely: nozzle subtends ~120° of runner circumference; lambda ≈ 0.333


def design(H: float, Q: float, eta_assumed: float = 0.80,
           alpha_deg: float = ALPHA_DEG,
           nozzle_arc_deg: float = 30.0) -> dict:
    """
    Compute Crossflow turbine design parameters from site measurements.

    Parameters
    ----------
    H              : gross head, m
    Q              : design flow rate, m³/s
    eta_assumed    : expected overall efficiency (used for power estimate only)
    alpha_deg      : nozzle jet angle, degrees (default 16°, optimal per Quaranta 2022)
    nozzle_arc_deg : effective nozzle throat opening arc at the runner, degrees.
                     Smaller = wider runner. Typical range 25–45°; default 30°.

    Returns
    -------
    dict with all design parameters (SI units unless noted)
    """
    alpha = math.radians(alpha_deg)

    # ── 1. Net head ──────────────────────────────────────────────────────────
    Hn = ETA_HYD * H

    # ── 2. Nozzle jet velocity ───────────────────────────────────────────────
    V = CV * math.sqrt(2 * G * Hn)

    # ── 3. Inlet blade angle (β1) from velocity triangle ────────────────────
    # tan(β1) = 2·tan(α)  [Quaranta 2022, Eq. 9]
    beta1 = math.atan(2 * math.tan(alpha))
    beta1_deg = math.degrees(beta1)
    beta2_deg = 90.0  # exit angle (ideal)

    # ── 4. Dimensionless flow (Q*) ───────────────────────────────────────────
    # Q* = Q / (Hn² · sqrt(2g·Hn))  [Quaranta 2022, Eq. 22]
    Q_star = Q / (Hn**2 * math.sqrt(2 * G * Hn))

    # ── 5. Dimensionless speed (N*) — Quaranta 2022, Eq. 24 ─────────────────
    N_star = 4.805 * Q_star**(-0.448)

    # ── 6. Rotational speed (rpm) ────────────────────────────────────────────
    # N* = N[rpm] · Hn[m] / sqrt(2g·Hn)[m/s]  — Quaranta 2022 footnote 1 explicitly
    # mixes units (N in rpm, denominator in 1/s) so rearranging gives rpm directly.
    N_rpm_raw = N_star * math.sqrt(2 * G * Hn) / Hn

    # Specific speed Ns for correction factor selection
    # Ns = N · Q^0.5 / Hn^0.75  (turbine convention, rpm-m³/s-m)
    Ns = N_rpm_raw * math.sqrt(Q) / Hn**0.75

    # Correction factor (Quaranta 2022, Eq. 17)
    if Ns < 90:
        correction = 0.93
    else:
        correction = 1.35

    N = N_rpm_raw * correction  # final design speed, rpm
    omega = N * 2 * math.pi / 60  # angular velocity, rad/s

    # Recalculate Ns with corrected N
    Ns = N * math.sqrt(Q) / Hn**0.75

    # ── 7. Runner outer diameter (D1) ────────────────────────────────────────
    # From optimal speed ratio: u1 = SR_OPT·V → u1 = ω·R1
    # Also from Quaranta Eq. 14: D1 = 84.6·SR_OPT·cos(α)·√Hn / N
    u1 = SR_OPT * V
    R1 = u1 / omega          # outer radius, m
    D1 = 2 * R1              # outer diameter, m

    # ── 8. Inner diameter (D2) ───────────────────────────────────────────────
    D2 = D_RATIO * D1
    R2 = D2 / 2

    # ── 9. Blade curvature radius (ρb) ───────────────────────────────────────
    # ρb = (R1² - R2²) / (2·R1·cos(β1))  [Quaranta 2022, Eq. 10]
    rho_b = (R1**2 - R2**2) / (2 * R1 * math.cos(beta1))

    # ── 10. Blade central angle (δ) ──────────────────────────────────────────
    # tan(δ/2) = cos(β1) / (sin(β1) + R2/R1)  [Quaranta 2022, Eq. 11]
    tan_half_delta = math.cos(beta1) / (math.sin(beta1) + R2 / R1)
    delta = 2 * math.atan(tan_half_delta)
    delta_deg = math.degrees(delta)

    # ── 11. Nozzle geometry ───────────────────────────────────────────────────
    # Nozzle subtends angle λ_rad around runner circumference
    # Typical nozzle arc: 120° → λ_rad = 2π/3
    # Runner axial width from continuity through the nozzle throat arc:
    # Q = V·sin(α) · (R1·λ) · B  →  B = Q / (V·sin(α)·R1·λ)
    # λ is the nozzle throat opening arc at the outer runner radius.
    lambda_rad = math.radians(nozzle_arc_deg)
    B = Q / (V * math.sin(alpha) * R1 * lambda_rad)

    # Nozzle throat width ≈ runner width (same axial dimension)
    b = B

    # ── 13. Number of blades (Nb) ────────────────────────────────────────────
    # Condition: blade pitch at outer radius = ρb · cos(β1)
    # → Nb = 2π·R1 / (ρb · cos(β1))
    # For standard design constants (α=16°, D2/D1=0.665) this simplifies to
    # 4π/(1-D_RATIO²) ≈ 22.5 → 23 blades.
    Nb_float = 2 * math.pi * R1 / (rho_b * math.cos(beta1))
    Nb = max(15, int(round(Nb_float)))

    # ── 14. Power estimate ───────────────────────────────────────────────────
    P = eta_assumed * 1000 * G * Q * H  # watts
    P_kW = P / 1000

    # ── 15. Peripheral velocity and velocity ratio ────────────────────────────
    u1_check = omega * R1
    speed_ratio = u1_check / V

    return {
        # Site inputs
        "H_gross_m":      H,
        "Q_m3s":          Q,
        "eta_assumed":    eta_assumed,
        # Net head & velocities
        "Hn_m":           Hn,
        "V_jet_ms":       V,
        "u1_ms":          u1,
        "speed_ratio":    speed_ratio,
        # Angles
        "alpha_deg":      alpha_deg,
        "beta1_deg":      beta1_deg,
        "beta2_deg":      beta2_deg,
        "delta_deg":      delta_deg,
        # Dimensionless parameters
        "Q_star":         Q_star,
        "N_star":         N_star,
        "Ns":             Ns,
        # Rotational speed
        "N_rpm":          N,
        "omega_rads":     omega,
        # Runner geometry
        "D1_m":           D1,
        "R1_m":           R1,
        "D2_m":           D2,
        "R2_m":           R2,
        "B_m":            B,
        # Blade geometry
        "rho_b_m":        rho_b,
        "Nb":             Nb,
        # Nozzle
        "b_m":            b,
        "lambda_rad":     lambda_rad,
        # Power
        "P_kW":           P_kW,
    }


def print_summary(p: dict) -> None:
    """Print a formatted design summary."""
    sep = "─" * 52

    print(f"\n{'═'*52}")
    print(f"  CROSSFLOW TURBINE DESIGN SUMMARY")
    print(f"{'═'*52}")

    print(f"\n  SITE CONDITIONS")
    print(sep)
    print(f"  Gross head (H)          : {p['H_gross_m']:.2f} m")
    print(f"  Net head (Hn)           : {p['Hn_m']:.2f} m")
    print(f"  Flow rate (Q)           : {p['Q_m3s']:.4f} m³/s")
    print(f"  Estimated power         : {p['P_kW']:.2f} kW")
    print(f"  Assumed efficiency      : {p['eta_assumed']*100:.0f} %")

    print(f"\n  HYDRAULICS")
    print(sep)
    print(f"  Jet velocity (V)        : {p['V_jet_ms']:.3f} m/s")
    print(f"  Peripheral vel. (u1)    : {p['u1_ms']:.3f} m/s")
    print(f"  Speed ratio (u1/V)      : {p['speed_ratio']:.4f}  (opt ≈ 0.565)")
    print(f"  Nozzle angle (α)        : {p['alpha_deg']:.1f}°")
    print(f"  Inlet blade angle (β1)  : {p['beta1_deg']:.2f}°")
    print(f"  Exit blade angle (β2)   : {p['beta2_deg']:.1f}°  (ideal)")
    print(f"  Blade central angle (δ) : {p['delta_deg']:.2f}°")

    print(f"\n  DIMENSIONLESS PARAMETERS")
    print(sep)
    print(f"  Q*                      : {p['Q_star']:.6f}")
    print(f"  N*                      : {p['N_star']:.4f}")
    print(f"  Specific speed (Ns)     : {p['Ns']:.2f}  rpm·(m³/s)^0.5/m^0.75")

    def mm_in(m): return f"{m*1000:.1f} mm  ({m*1000/25.4:.2f} in)"

    print(f"\n  RUNNER GEOMETRY")
    print(sep)
    print(f"  Rotational speed (N)    : {p['N_rpm']:.1f} rpm")
    print(f"  Outer diameter (D1)     : {mm_in(p['D1_m'])}")
    print(f"  Inner diameter (D2)     : {mm_in(p['D2_m'])}")
    print(f"  Axial width (B)         : {mm_in(p['B_m'])}")
    print(f"  Blade curvature (ρb)    : {mm_in(p['rho_b_m'])}")
    print(f"  Number of blades (Nb)   : {p['Nb']}")

    print(f"\n  NOZZLE")
    print(sep)
    print(f"  Nozzle width (b)        : {p['b_m']*1000:.1f} mm")
    print(f"  Nozzle arc              : {math.degrees(p['lambda_rad']):.1f}°")

    print(f"\n{'═'*52}\n")


if __name__ == "__main__":
    # Quick sanity check: Quaranta 2022 Table 4, Case 2 → H=10m, Q=0.5 m³/s
    params = design(H=10.0, Q=0.5)
    print_summary(params)
