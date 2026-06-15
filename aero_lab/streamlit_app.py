from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from aero_lab.calc.airfoil import (
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
    coefficients = estimate_coefficients(settings)
    field = flow_field(settings)
    outline_x, outline_y = airfoil_outline(settings)

    metric_cols = st.columns(5)
    metric_cols[0].metric("Wind speed", f"{settings.wind_speed:.0f} m/s")
    metric_cols[1].metric("Effective AoA", f"{coefficients.effective_angle_degrees:.1f} deg")
    metric_cols[2].metric("Lift / downforce", f"{coefficients.lift_newtons:,.0f} N")
    metric_cols[3].metric("Drag", f"{coefficients.drag_newtons:,.0f} N")
    metric_cols[4].metric("L/D", f"{_safe_ratio(coefficients.lift_newtons, coefficients.drag_newtons):.2f}")

    canvas_tab, stream_tab, pressure_tab, distribution_tab, coefficients_tab = st.tabs(
        ["Live Canvas", "Streamlines", "Pressure Field", "Surface Pressure", "Lift & Drag"]
    )

    with canvas_tab:
        components.html(render_canvas_html(settings, coefficients), height=650, scrolling=False)

    with stream_tab:
        st.plotly_chart(_streamline_figure(field, outline_x, outline_y), use_container_width=True)

    with pressure_tab:
        st.plotly_chart(_pressure_field_figure(field, outline_x, outline_y), use_container_width=True)

    with distribution_tab:
        st.plotly_chart(_pressure_distribution_figure(settings), use_container_width=True)

    with coefficients_tab:
        st.plotly_chart(_coefficient_figure(settings), use_container_width=True)


def _sidebar_settings() -> AirfoilSettings:
    st.sidebar.header("Airfoil Setup")
    wind_speed = st.sidebar.slider("Wind speed (m/s)", 10.0, 95.0, 45.0, 1.0)
    angle_of_attack = st.sidebar.slider("Angle of attack (deg)", -8.0, 18.0, 6.0, 0.25)
    chord = st.sidebar.slider("Chord length (m)", 0.5, 3.0, 1.0, 0.05)
    thickness = st.sidebar.slider("Thickness ratio", 0.06, 0.20, 0.12, 0.005)
    camber = st.sidebar.slider("Base camber", 0.0, 0.12, 0.035, 0.002)

    st.sidebar.header("F1 Wing Placeholders")
    front_wing = st.sidebar.slider("Front wing flap (deg)", -5.0, 35.0, 0.0, 0.5)
    rear_wing = st.sidebar.slider("Rear wing flap (deg)", -5.0, 45.0, 0.0, 0.5)

    st.sidebar.header("Reference")
    area = st.sidebar.slider("Reference area (m^2)", 0.2, 4.0, 1.0, 0.1)
    density = st.sidebar.slider("Air density (kg/m^3)", 0.9, 1.4, 1.225, 0.005)

    st.sidebar.caption("Front/rear wing degree effects are isolated in `aero_lab.calc.airfoil.wing_adjustment()`.")
    _cad_import_placeholder()

    return AirfoilSettings(
        wind_speed=wind_speed,
        angle_of_attack_degrees=angle_of_attack,
        front_wing_degrees=front_wing,
        rear_wing_degrees=rear_wing,
        chord=chord,
        thickness_ratio=thickness,
        camber=camber,
        air_density=density,
        reference_area=area,
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
            wind_speed=settings.wind_speed,
            angle_of_attack_degrees=float(angle),
            front_wing_degrees=settings.front_wing_degrees,
            rear_wing_degrees=settings.rear_wing_degrees,
            chord=settings.chord,
            thickness_ratio=settings.thickness_ratio,
            camber=settings.camber,
            air_density=settings.air_density,
            reference_area=settings.reference_area,
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


if __name__ == "__main__":
    main()
