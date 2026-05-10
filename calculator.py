"""
Crossflow (Banki-Michell) hydro turbine design calculator.

Primary reference: Quaranta et al. (2022) — dimensionless design methodology.
"""

import math


G = 9.81   # m/s²
CV = 0.98  # nozzle velocity coefficient (atmospheric inlet)

# Quaranta 2022, Section 3 design constants
ALPHA_DEG = 22.0   # jet angle — 22° optimises efficiency (Perez-Rodriguez 2021)
SR_OPT    = 0.565  # optimal speed ratio = 1.13 × SRth (1.13 × 0.5)
D_RATIO   = 0.665  # D2/D1 inner-to-outer diameter ratio (average literature value)
LAMBDA    = math.pi / 2  # nozzle entry arc, fixed at 90° (Section 3.1)
B_RATIO   = 1.5    # runner width / nozzle width (Eq. 21)
ETA_HYD   = 0.94   # Hn ≈ 0.94 H (Nasir 2013)


def design(H: float, Q: float,
           eta_assumed: float = 0.80,
           alpha_deg: float = ALPHA_DEG) -> dict:
    """
    Compute crossflow turbine design parameters.

    Parameters
    ----------
    H           : gross head, m
    Q           : design flow rate, m³/s
    eta_assumed : expected overall efficiency (power estimate + Ns)
    alpha_deg   : nozzle jet angle, degrees (default 22°, Quaranta 2022 Section 3.1)

    Returns
    -------
    dict with all design parameters in SI units
    """
    alpha = math.radians(alpha_deg)

    # 1. Net head
    Hn = ETA_HYD * H

    # 2. Jet velocity (Eq. 4)
    V = CV * math.sqrt(2 * G * Hn)

    # 3. Blade inlet angle β1 from velocity triangle (Eq. 9)
    beta1 = math.atan(2 * math.tan(alpha))
    beta1_deg = math.degrees(beta1)

    # 4. Power estimate for Ns calculation
    P_kW = eta_assumed * 9.81 * Q * Hn  # = η·ρ·g·Q·Hn / 1000

    # 5. Dimensionless flow Q* (Eq. 23)
    Q_star = Q / (Hn**2 * math.sqrt(2 * G * Hn))

    # 6. Dimensionless speed N* (Eq. 24)
    N_star = 4.805 * Q_star**(-0.448)

    # 7. Preliminary rotational speed (rpm) — Eq. 22, footnote 1 intentionally
    #    mixes rpm at numerator with 1/s at denominator; no 60/2π conversion needed
    N_rpm_raw = N_star * math.sqrt(2 * G * Hn) / Hn

    # 8. Characteristic speed Ns (Eq. 1) — power-based, rpm·kW^0.5·m^-1.25
    Ns = N_rpm_raw * math.sqrt(P_kW) / Hn**1.25

    # 9. Correction factor (Quaranta 2022, Fig. 8)
    correction = 0.93 if Ns < 90 else 1.35
    N = N_rpm_raw * correction
    omega = N * 2 * math.pi / 60

    # Recompute Ns with corrected N
    Ns = N * math.sqrt(P_kW) / Hn**1.25

    # 10. Outer diameter D1 from optimal speed ratio (Eqs. 3–5, Section 3.2)
    u1 = SR_OPT * V * math.cos(alpha)  # u1 = SRopt × Vu = SRopt × V·cos(α)
    R1 = u1 / omega
    D1 = 2 * R1

    # 11. Inner diameter D2 (Section 3.2)
    D2 = D_RATIO * D1
    R2 = D2 / 2

    # 12. Blade curvature radius ρb (Eq. 14, with β2=90° so cos β2=0)
    rho_b = (R1**2 - R2**2) / (2 * R1 * math.cos(beta1))

    # 13. Blade central angle δ (Eq. 15, with β2=90°, sin β2=1)
    tan_half_delta = math.cos(beta1) / (math.sin(beta1) + R2 / R1)
    delta = 2 * math.atan(tan_half_delta)
    delta_deg = math.degrees(delta)

    # 14. Nozzle width b and runner width B
    #     Continuity through nozzle arc (Eq. 17): Q = b·V·sin(α)·λ·R1
    #     λ = π/2 (fixed at 90°, Section 3.1)
    b = Q / (V * math.sin(alpha) * LAMBDA * R1)
    B = B_RATIO * b  # Eq. 21

    # 15. Number of blades (Fig. 11 parabolic equation, valid 40 < Ns < 110)
    #     Nb,opt / Nb,Mockmore = −0.0008·Ns² + 0.1257·Ns − 3.5261
    #     Nb,Mockmore = π·sin(β1) / k,  k = 0.087
    Nb_mockmore = math.pi * math.sin(beta1) / 0.087
    Ns_clamped = max(40.0, min(Ns, 110.0))
    ratio = -0.0008 * Ns_clamped**2 + 0.1257 * Ns_clamped - 3.5261
    Nb = max(15, round(Nb_mockmore * ratio))

    return {
        "H_gross_m":   H,
        "Q_m3s":       Q,
        "eta_assumed": eta_assumed,
        "Hn_m":        Hn,
        "V_jet_ms":    V,
        "u1_ms":       u1,
        "alpha_deg":   alpha_deg,
        "beta1_deg":   beta1_deg,
        "beta2_deg":   90.0,
        "delta_deg":   delta_deg,
        "Q_star":      Q_star,
        "N_star":      N_star,
        "Ns":          Ns,
        "N_rpm":       N,
        "omega_rads":  omega,
        "D1_m":        D1,
        "R1_m":        R1,
        "D2_m":        D2,
        "R2_m":        R2,
        "B_m":         B,
        "rho_b_m":     rho_b,
        "Nb":          Nb,
        "b_m":         b,
        "lambda_rad":  LAMBDA,
        "P_kW":        P_kW,
    }


def print_summary(p: dict) -> None:
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

    def mm_in(m): return f"{m*1000:.1f} mm  ({m*1000/25.4:.2f} in)"

    print(f"\n  HYDRAULICS")
    print(sep)
    print(f"  Jet velocity (V)        : {p['V_jet_ms']:.3f} m/s")
    print(f"  Peripheral vel. (u1)    : {p['u1_ms']:.3f} m/s")
    print(f"  Nozzle angle (α)        : {p['alpha_deg']:.1f}°")
    print(f"  Inlet blade angle (β1)  : {p['beta1_deg']:.2f}°")
    print(f"  Exit blade angle (β2)   : {p['beta2_deg']:.1f}°")
    print(f"  Blade central angle (δ) : {p['delta_deg']:.2f}°")

    print(f"\n  DIMENSIONLESS PARAMETERS")
    print(sep)
    print(f"  Q*                      : {p['Q_star']:.6f}")
    print(f"  N*                      : {p['N_star']:.4f}")
    print(f"  Characteristic speed Ns : {p['Ns']:.1f}")

    print(f"\n  RUNNER GEOMETRY")
    print(sep)
    print(f"  Rotational speed (N)    : {p['N_rpm']:.1f} rpm")
    print(f"  Outer diameter (D1)     : {mm_in(p['D1_m'])}")
    print(f"  Inner diameter (D2)     : {mm_in(p['D2_m'])}")
    print(f"  Runner width (B)        : {mm_in(p['B_m'])}")
    print(f"  Nozzle width (b)        : {mm_in(p['b_m'])}")
    print(f"  Blade curvature (ρb)    : {mm_in(p['rho_b_m'])}")
    print(f"  Number of blades (Nb)   : {p['Nb']}")

    print(f"\n{'═'*52}\n")


if __name__ == "__main__":
    # Validation: Quaranta 2022 Table 4, Case 2 — expect N≈231rpm, D1≈595mm, b≈208mm
    p = design(H=10.0, Q=0.5)
    print_summary(p)
