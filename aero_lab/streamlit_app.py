from __future__ import annotations

from dataclasses import replace

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from aero_lab.calc.airfoil import (
    AeroCoefficients,
    AirfoilSettings,
    airfoil_outline,
    estimate_coefficients,
    flow_field,
    pressure_distribution,
    streamline_paths,
)
from aero_lab.cad.adapters import supported_cad_extensions
from aero_lab.frontend.canvas_component import render_canvas_html


def main() -> None:
    st.set_page_config(page_title="Aero Lab", layout="wide")
    st.title("Aero Lab")

    settings = _sidebar_settings()
    page = st.sidebar.radio("Page", ("Live Tunnel", "Graphs"), index=0)
    coefficients = estimate_coefficients(settings)
    reference_coefficients = estimate_coefficients(AirfoilSettings())

    _summary_metrics(settings, coefficients, reference_coefficients)

    if page == "Live Tunnel":
        components.html(render_canvas_html(settings, coefficients), height=650, scrolling=False)
        return

    _graphs_page(settings)


def _summary_metrics(
    settings: AirfoilSettings,
    coefficients: AeroCoefficients,
    reference_coefficients: AeroCoefficients,
) -> None:
    top_metric_cols = st.columns(4)
    top_metric_cols[0].metric("Vehicle speed", f"{settings.wind_speed:.1f} m/s")
    top_metric_cols[1].metric("Effective AoA", f"{coefficients.effective_angle_degrees:.1f} deg")
    top_metric_cols[2].metric("Reynolds number", _format_reynolds(coefficients.reynolds_number))
    top_metric_cols[3].metric("Dynamic pressure", f"{coefficients.dynamic_pressure_pascals:,.0f} Pa")

    force_metric_cols = st.columns(6)
    force_metric_cols[0].metric("Flow regime", coefficients.flow_regime.title())
    force_metric_cols[1].metric("Skin drag", f"{coefficients.skin_friction_drag_newtons:,.0f} N")
    force_metric_cols[2].metric("Pressure drag", f"{coefficients.pressure_drag_newtons:,.0f} N")
    force_metric_cols[3].metric(
        "Lift / downforce",
        f"{coefficients.lift_newtons:,.0f} N",
        delta=_format_force_delta(coefficients.lift_newtons, reference_coefficients.lift_newtons),
    )
    force_metric_cols[4].metric(
        "Drag",
        f"{coefficients.drag_newtons:,.0f} N",
        delta=_format_force_delta(coefficients.drag_newtons, reference_coefficients.drag_newtons),
    )
    force_metric_cols[5].metric("L/D", f"{_safe_ratio(coefficients.lift_newtons, coefficients.drag_newtons):.2f}")
    st.caption("Flow regime is classified from Reynolds number; true turbulent eddies are not visualized yet.")


def _graphs_page(settings: AirfoilSettings) -> None:
    field = flow_field(settings)
    outline_x, outline_y = airfoil_outline(settings)
    stream_tab, pressure_tab, distribution_tab, coefficients_tab = st.tabs(
        ["Streamlines", "Pressure Field", "Surface Pressure", "Lift & Drag"]
    )

    with stream_tab:
        st.plotly_chart(_streamline_figure(field, outline_x, outline_y), width="stretch")

    with pressure_tab:
        st.plotly_chart(_pressure_field_figure(field, outline_x, outline_y), width="stretch")

    with distribution_tab:
        st.plotly_chart(_pressure_distribution_figure(settings), width="stretch")

    with coefficients_tab:
        st.plotly_chart(_coefficient_figure(settings), width="stretch")
        st.plotly_chart(_force_sweep_figure(settings), width="stretch")


def _sidebar_settings() -> AirfoilSettings:
    st.sidebar.header("Airfoil Setup")
    speed_unit = st.sidebar.selectbox("Vehicle speed units", ("m/s", "km/h", "mph"), index=1)
    min_speed = _speed_from_mps(10.0, speed_unit)
    max_speed = _speed_from_mps(95.0, speed_unit)
    default_speed = _speed_from_mps(45.0, speed_unit)
    speed_step = {"m/s": 1.0, "km/h": 5.0, "mph": 2.5}[speed_unit]
    vehicle_speed = st.sidebar.slider(
        f"Vehicle speed ({speed_unit})",
        min_speed,
        max_speed,
        default_speed,
        speed_step,
    )
    wind_speed = _speed_to_mps(vehicle_speed, speed_unit)
    angle_of_attack = 6.0
    st.sidebar.caption("Angle of attack is locked at 6.0 deg while the flow model is being stabilized.")
    chord = st.sidebar.slider("Chord length (m)", 0.5, 3.0, 1.0, 0.05)
    span = st.sidebar.slider("Span / width (m)", 0.5, 3.0, 1.0, 0.05)
    thickness = st.sidebar.slider("Thickness ratio", 0.06, 0.20, 0.12, 0.005)
    camber = st.sidebar.slider("Base camber", 0.0, 0.12, 0.035, 0.002)

    st.sidebar.header("Object Dimensions")
    body_length = st.sidebar.slider("Body length (m)", 0.5, 5.0, chord, 0.05)
    body_width = st.sidebar.slider("Body width (m)", 0.2, 3.0, span, 0.05)
    body_height = st.sidebar.slider("Body height (m)", 0.05, 1.5, chord * thickness, 0.01)

    st.sidebar.header("F1 Wing Placeholders")
    front_wing = 0.0
    rear_wing = 0.0
    st.sidebar.caption("Front/rear wing flap degrees are locked while those adjustment formulas are in development.")

    st.sidebar.header("Reference")
    density = st.sidebar.slider("Air density (kg/m^3)", 0.9, 1.4, 1.225, 0.005)
    viscosity = st.sidebar.number_input(
        "Dynamic viscosity (Pa*s)",
        min_value=1.0e-6,
        max_value=5.0e-5,
        value=1.81e-5,
        step=0.01e-5,
        format="%.2e",
    )

    st.sidebar.caption("Front/rear wing degree effects are isolated in `aero_lab.calc.airfoil.wing_adjustment()`.")
    _cad_import_placeholder()

    return AirfoilSettings(
        shape_model="simple_body",
        wind_speed=wind_speed,
        angle_of_attack_degrees=angle_of_attack,
        front_wing_degrees=front_wing,
        rear_wing_degrees=rear_wing,
        chord=chord,
        span=span,
        body_length=body_length,
        body_width=body_width,
        body_height=body_height,
        thickness_ratio=thickness,
        camber=camber,
        air_density=density,
        dynamic_viscosity=viscosity,
        reference_area=chord * span,
        frontal_area=body_width * body_height,
        wetted_area=2.0 * (body_length * body_width + body_length * body_height + body_width * body_height),
    )


def _cad_import_placeholder() -> None:
    with st.sidebar.expander("3D CAD testing"):
        extensions = [extension.lstrip(".") for extension in supported_cad_extensions()]
        uploaded = st.file_uploader("CAD or mesh file", type=extensions)
        if uploaded is not None:
            st.warning("CAD parsing is reserved for the future 3D viewer path.")
        st.caption("Import hooks live in `aero_lab.cad.adapters`.")


def _streamline_figure(field: dict[str, np.ndarray], outline_x: np.ndarray, outline_y: np.ndarray) -> go.Figure:
    figure = _base_flow_figure("Streamlines")
    speed = field["speed"]
    figure.add_trace(
        go.Heatmap(
            x=field["x"][0],
            y=field["y"][:, 0],
            z=speed,
            colorscale="Viridis",
            showscale=True,
            colorbar={"title": "m/s"},
            opacity=0.55,
        )
    )
    for xs, ys in streamline_paths(field):
        figure.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": "white", "width": 1.4},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    _add_airfoil(figure, outline_x, outline_y)
    return figure


def _pressure_field_figure(field: dict[str, np.ndarray], outline_x: np.ndarray, outline_y: np.ndarray) -> go.Figure:
    figure = _base_flow_figure("Pressure Coefficient Field")
    figure.add_trace(
        go.Heatmap(
            x=field["x"][0],
            y=field["y"][:, 0],
            z=field["cp"],
            colorscale="RdBu",
            reversescale=True,
            zmid=0,
            colorbar={"title": "Cp"},
        )
    )
    _add_airfoil(figure, outline_x, outline_y)
    return figure


def _pressure_distribution_figure(settings: AirfoilSettings) -> go.Figure:
    x, upper_cp, lower_cp = pressure_distribution(settings)
    figure = go.Figure()
    figure.add_trace(go.Scatter(x=x, y=upper_cp, mode="lines", name="Upper surface"))
    figure.add_trace(go.Scatter(x=x, y=lower_cp, mode="lines", name="Lower surface"))
    figure.update_layout(
        height=560,
        xaxis_title="Chord position x/c",
        yaxis_title="Pressure coefficient Cp",
        yaxis={"autorange": "reversed", "zeroline": True},
        margin={"l": 20, "r": 20, "t": 35, "b": 20},
    )
    return figure


def _coefficient_figure(settings: AirfoilSettings) -> go.Figure:
    angles = np.linspace(-8.0, 18.0, 80)
    lift_values = []
    drag_values = []
    for angle in angles:
        adjusted = AirfoilSettings(
            shape_model=settings.shape_model,
            wind_speed=settings.wind_speed,
            angle_of_attack_degrees=float(angle),
            front_wing_degrees=settings.front_wing_degrees,
            rear_wing_degrees=settings.rear_wing_degrees,
            chord=settings.chord,
            span=settings.span,
            body_length=settings.body_length,
            body_width=settings.body_width,
            body_height=settings.body_height,
            thickness_ratio=settings.thickness_ratio,
            camber=settings.camber,
            air_density=settings.air_density,
            dynamic_viscosity=settings.dynamic_viscosity,
            reference_area=settings.reference_area,
            frontal_area=settings.frontal_area,
            wetted_area=settings.wetted_area,
        )
        coeffs = estimate_coefficients(adjusted)
        lift_values.append(coeffs.lift_coefficient)
        drag_values.append(coeffs.drag_coefficient)

    figure = go.Figure()
    figure.add_trace(go.Scatter(x=angles, y=lift_values, mode="lines", name="CL"))
    figure.add_trace(go.Scatter(x=angles, y=drag_values, mode="lines", name="CD", yaxis="y2"))
    figure.add_vline(x=settings.angle_of_attack_degrees, line_dash="dot", line_color="#888")
    figure.update_layout(
        height=560,
        xaxis_title="Angle of attack (deg)",
        yaxis={"title": "CL"},
        yaxis2={"title": "CD", "overlaying": "y", "side": "right"},
        margin={"l": 20, "r": 20, "t": 35, "b": 20},
    )
    return figure


def _force_sweep_figure(settings: AirfoilSettings) -> go.Figure:
    speeds = np.linspace(10.0, 95.0, 80)
    lift_values = []
    drag_values = []
    reynolds_values = []
    for speed in speeds:
        coeffs = estimate_coefficients(replace(settings, wind_speed=float(speed)))
        lift_values.append(coeffs.lift_newtons)
        drag_values.append(coeffs.drag_newtons)
        reynolds_values.append(coeffs.reynolds_number)

    figure = go.Figure()
    figure.add_trace(go.Scatter(x=speeds, y=lift_values, mode="lines", name="Lift / downforce"))
    figure.add_trace(go.Scatter(x=speeds, y=drag_values, mode="lines", name="Drag"))
    figure.add_trace(
        go.Scatter(
            x=speeds,
            y=reynolds_values,
            mode="lines",
            name="Re",
            yaxis="y2",
            line={"dash": "dot"},
        )
    )
    figure.add_vline(x=settings.wind_speed, line_dash="dot", line_color="#888")
    figure.update_layout(
        height=520,
        title="Force Changes with Vehicle Speed",
        xaxis_title="Vehicle speed (m/s)",
        yaxis={"title": "Force (N)"},
        yaxis2={"title": "Re", "overlaying": "y", "side": "right"},
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
    )
    return figure


def _base_flow_figure(title: str) -> go.Figure:
    figure = go.Figure()
    figure.update_layout(
        title=title,
        height=650,
        plot_bgcolor="#07111f",
        paper_bgcolor="#07111f",
        font={"color": "#f5f7fa"},
        xaxis={"scaleanchor": "y", "showgrid": False, "zeroline": False, "title": "x / chord"},
        yaxis={"showgrid": False, "zeroline": False, "title": "y / chord"},
        margin={"l": 20, "r": 20, "t": 45, "b": 20},
    )
    return figure


def _add_airfoil(figure: go.Figure, outline_x: np.ndarray, outline_y: np.ndarray) -> None:
    figure.add_trace(
        go.Scatter(
            x=outline_x,
            y=outline_y,
            fill="toself",
            mode="lines",
            line={"color": "#f3f6f4", "width": 2},
            fillcolor="#d8dee9",
            name="Airfoil",
        )
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(denominator) < 1e-9:
        return 0.0
    return numerator / denominator


def _speed_to_mps(speed: float, unit: str) -> float:
    if unit == "km/h":
        return speed / 3.6
    if unit == "mph":
        return speed * 0.44704
    return speed


def _speed_from_mps(speed: float, unit: str) -> float:
    if unit == "km/h":
        return speed * 3.6
    if unit == "mph":
        return speed / 0.44704
    return speed


def _format_reynolds(value: float) -> str:
    if abs(value) >= 1.0e6:
        return f"{value / 1.0e6:.2f}M"
    if abs(value) >= 1.0e3:
        return f"{value / 1.0e3:.1f}k"
    return f"{value:.0f}"


def _format_length(value: float) -> str:
    if abs(value) < 0.001:
        return f"{value * 1_000_000:.0f} um"
    if abs(value) < 1.0:
        return f"{value * 1000:.1f} mm"
    return f"{value:.3f} m"


def _format_force_delta(current: float, reference: float) -> str:
    delta = current - reference
    return f"{delta:+,.0f} N vs default"


if __name__ == "__main__":
    main()
