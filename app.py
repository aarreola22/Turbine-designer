"""
Crossflow Turbine Designer — Streamlit web app.

Run with:
  source .venv/bin/activate
  streamlit run app.py
"""

import tempfile
from pathlib import Path

import streamlit as st

from calculator import design

st.set_page_config(
    page_title="Crossflow Turbine Designer",
    page_icon="💧",
    layout="wide",
)

st.title("💧 Crossflow Turbine Designer")
st.caption("Banki-Michell crossflow hydro turbine — design methodology from Quaranta et al. (2022)")

st.divider()

# ── Input panel ──────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.6], gap="large")

with left:
    st.subheader("Site Parameters")

    units = st.radio("Units", ["Imperial  (ft, cfs)", "Metric  (m, m³/s)"],
                     horizontal=True, label_visibility="collapsed")
    imperial = units.startswith("Imperial")

    if imperial:
        h_disp = st.number_input("Gross head (ft)", min_value=5.0, max_value=2000.0,
                                  value=120.0, step=1.0)
        q_disp = st.number_input("Flow rate (cfs)", min_value=0.1, max_value=5000.0,
                                  value=18.0, step=0.5)
        H = h_disp * 0.3048
        Q = q_disp * 0.028316847
        st.caption(f"→  {H:.2f} m  ·  {Q:.4f} m³/s")
    else:
        H = st.number_input("Gross head (m)", min_value=1.5, max_value=600.0,
                             value=10.0, step=0.5)
        Q = st.number_input("Flow rate (m³/s)", min_value=0.01, max_value=200.0,
                             value=0.5, step=0.05)

    with st.expander("Advanced settings"):
        eta = st.slider("Efficiency estimate", 0.60, 0.92, 0.80, 0.01,
                        help="Used for the power estimate only")
        alpha_deg = st.slider("Nozzle jet angle α (°)", 16, 30, 22,
                              help="Angle of the jet to the runner tangent — 22° is optimal (Quaranta 2022)")

    st.button("Calculate", type="primary", use_container_width=True, key="calc_btn")


# ── Calculation ───────────────────────────────────────────────────────────────
run_calc = st.session_state.get("calc_btn") or "p" not in st.session_state

if run_calc:
    st.session_state.p = design(
        H=H, Q=Q,
        eta_assumed=eta,
        alpha_deg=alpha_deg,
    )
    st.session_state.model_ready = False

p = st.session_state.get("p")


# ── Results panel ─────────────────────────────────────────────────────────────
def _table(rows):
    """Render a Parameter / Metric / Imperial table."""
    header = "| Parameter | Metric | Imperial |\n|---|---|---|\n"
    body = "\n".join(f"| {r[0]} | {r[1]} | {r[2]} |" for r in rows)
    st.markdown(header + body)


if p:
    with right:
        st.subheader("Design Results")

        # ── Top-line performance ──────────────────────────────────────────────
        c1, c2, c3 = st.columns(3)
        c1.metric("Estimated Power",  f"{p['P_kW']:.1f} kW",
                  f"{p['P_kW'] * 1.341:.1f} hp")
        c2.metric("Rotational Speed", f"{p['N_rpm']:.0f} rpm")
        c3.metric("Specific Speed Ns", f"{p['Ns']:.1f}")

        st.divider()

        # ── Runner geometry ───────────────────────────────────────────────────
        st.markdown("**Runner Geometry**")
        _table([
            ("Outer diameter  D1",   f"{p['D1_m']*1000:.1f} mm",  f"{p['D1_m']*1000/25.4:.2f} in"),
            ("Inner diameter  D2",   f"{p['D2_m']*1000:.1f} mm",  f"{p['D2_m']*1000/25.4:.2f} in"),
            ("Axial width  B",        f"{p['B_m']*1000:.1f} mm",   f"{p['B_m']*1000/25.4:.2f} in"),
            ("Blade curvature  ρb",  f"{p['rho_b_m']*1000:.1f} mm", f"{p['rho_b_m']*1000/25.4:.2f} in"),
            ("Number of blades  Nb", f"{p['Nb']}",                "—"),
        ])

        st.divider()

        # ── Hydraulics ────────────────────────────────────────────────────────
        st.markdown("**Hydraulics**")
        _table([
            ("Gross head  H",       f"{p['H_gross_m']:.2f} m",    f"{p['H_gross_m']*3.281:.1f} ft"),
            ("Net head  Hn",        f"{p['Hn_m']:.2f} m",         f"{p['Hn_m']*3.281:.1f} ft"),
            ("Flow rate  Q",        f"{p['Q_m3s']:.4f} m³/s",     f"{p['Q_m3s']/0.028317:.2f} cfs"),
            ("Jet velocity  V",     f"{p['V_jet_ms']:.2f} m/s",   f"{p['V_jet_ms']*3.281:.2f} ft/s"),
            ("Peripheral vel. u1",  f"{p['u1_ms']:.2f} m/s",      f"{p['u1_ms']*3.281:.2f} ft/s"),
            ("Inlet blade angle β₁", f"{p['beta1_deg']:.2f}°",    "—"),
            ("Blade central angle δ", f"{p['delta_deg']:.2f}°",   "—"),
        ])

        st.divider()

        # ── Nozzle ────────────────────────────────────────────────────────────
        st.markdown("**Nozzle**")
        _table([
            ("Nozzle width  b",     f"{p['b_m']*1000:.1f} mm",  f"{p['b_m']*1000/25.4:.2f} in"),
            ("Nozzle entry arc  λ", "90°", "—"),
        ])


# ── 3D Export ─────────────────────────────────────────────────────────────────
try:
    import cadquery as _cq
    HAS_CADQUERY = True
except ImportError:
    HAS_CADQUERY = False

if p:
    st.divider()
    st.subheader("3D Model Export")

    if not HAS_CADQUERY:
        st.info(
            "**3D export is available in the desktop version.**\n\n"
            "Install [Docker Desktop](https://www.docker.com/products/docker-desktop), "
            "then run:\n\n"
            "```\ndocker run -p 8501:8501 anarreol/turbine-designer\n```\n\n"
            "Open `http://localhost:8501` in your browser to get the full app with STEP and STL download."
        )
    else:
        st.caption("Generates a solid model of the runner (blades + end discs + shaft). "
                   "STEP opens in SolidWorks or Fusion 360; STL opens in Blender or goes to a 3D printer.")

        ec1, ec2, _ = st.columns([1, 1, 2])
        with ec1:
            blade_thick = st.number_input("Blade thickness (mm)", 1.0, 15.0, 3.0, 0.5)
        with ec2:
            shaft_r = st.number_input("Shaft radius (mm)", 5.0, 150.0, 20.0, 5.0)

        if st.button("Generate 3D Runner", type="secondary"):
            with st.spinner("Building geometry — this takes about 30–90 seconds…"):
                try:
                    from geometry import build_runner, export_step, export_stl

                    runner = build_runner(
                        p,
                        blade_thickness_mm=blade_thick,
                        shaft_radius_mm=shaft_r,
                    )

                    with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as f:
                        step_path = f.name
                    with tempfile.NamedTemporaryFile(suffix=".stl", delete=False) as f:
                        stl_path = f.name

                    export_step(runner, step_path)
                    export_stl(runner, stl_path)

                    st.session_state.step_bytes = Path(step_path).read_bytes()
                    st.session_state.stl_bytes  = Path(stl_path).read_bytes()
                    st.session_state.model_ready = True
                    st.success("3D model ready — click a button below to download.")

                except ImportError as exc:
                    st.error(f"CadQuery not available: {exc}")
                except Exception as exc:
                    st.error(f"Geometry error: {exc}")

        if st.session_state.get("model_ready"):
            dc1, dc2, _ = st.columns([1, 1, 2])
            dc1.download_button(
                "⬇ Download STEP",
                data=st.session_state.step_bytes,
                file_name="runner.step",
                mime="application/octet-stream",
                use_container_width=True,
            )
            dc2.download_button(
                "⬇ Download STL",
                data=st.session_state.stl_bytes,
                file_name="runner.stl",
                mime="application/octet-stream",
                use_container_width=True,
        )
