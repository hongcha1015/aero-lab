from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class AirfoilSettings:
    shape_model: str = "wing"
    wind_speed: float = 45.0
    angle_of_attack_degrees: float = 6.0
    front_wing_degrees: float = 0.0
    rear_wing_degrees: float = 0.0
    chord: float = 1.0
    span: float = 1.0
    body_length: float = 1.0
    body_width: float = 1.0
    body_height: float = 0.12
    thickness_ratio: float = 0.12
    camber: float = 0.035
    air_density: float = 1.225
    dynamic_viscosity: float = 1.81e-5
    reference_area: Optional[float] = None
    frontal_area: Optional[float] = None
    wetted_area: Optional[float] = None


@dataclass(frozen=True)
class AeroCoefficients:
    lift_coefficient: float
    drag_coefficient: float
    skin_friction_coefficient: float
    pressure_drag_coefficient: float
    lift_newtons: float
    drag_newtons: float
    skin_friction_drag_newtons: float
    pressure_drag_newtons: float
    effective_angle_degrees: float
    dynamic_pressure_pascals: float
    reference_area_m2: float
    frontal_area_m2: float
    wetted_area_m2: float
    reynolds_number: float
    flow_regime: str
    laminar_boundary_layer_m: float
    turbulent_boundary_layer_m: float
    circulation_m2_s: float
    lift_per_span_newtons_per_m: float


def wing_adjustment(settings: AirfoilSettings) -> tuple[float, float, float]:
    """Approximate F1 wing flap influence.

    This is deliberately isolated so it can be replaced with better data later.
    Positive front/rear wing degrees increase effective camber and downforce-like
    circulation. Rear wing is given more drag authority than front wing.
    """
    front = settings.front_wing_degrees
    rear = settings.rear_wing_degrees
    camber_delta = 0.0014 * front + 0.0019 * rear
    angle_delta = 0.10 * front + 0.16 * rear
    drag_delta = 0.00018 * front * front + 0.00032 * rear * rear
    return camber_delta, angle_delta, drag_delta


def estimate_coefficients(settings: AirfoilSettings) -> AeroCoefficients:
    if is_wing_model(settings):
        camber_delta, angle_delta, drag_delta = wing_adjustment(settings)
        effective_angle = settings.angle_of_attack_degrees + angle_delta
        alpha = np.radians(effective_angle)
        effective_camber = settings.camber + camber_delta
        lift_coefficient = 2.0 * np.pi * (alpha + effective_camber)
        lift_coefficient = float(np.clip(lift_coefficient, -3.2, 3.2))
    else:
        drag_delta = 0.0
        effective_angle = 0.0
        lift_coefficient = 0.0

    dynamic_pressure = 0.5 * settings.air_density * settings.wind_speed * settings.wind_speed
    reference_area = reference_area_m2(settings)
    frontal_area = frontal_area_m2(settings)
    wetted = wetted_area_m2(settings)
    reynolds = reynolds_number(settings)
    skin_friction_coefficient = average_skin_friction_coefficient(reynolds)
    pressure_drag_coefficient = pressure_drag_coefficient_estimate(settings, lift_coefficient, drag_delta)
    skin_friction_drag = dynamic_pressure * wetted * skin_friction_coefficient
    pressure_drag = dynamic_pressure * frontal_area * pressure_drag_coefficient
    drag = skin_friction_drag + pressure_drag
    drag_coefficient = drag / max(dynamic_pressure * frontal_area, 1e-12)
    lift = dynamic_pressure * reference_area * lift_coefficient
    laminar_boundary_layer, turbulent_boundary_layer = boundary_layer_thickness(settings, reynolds)
    circulation = circulation_from_lift_coefficient(settings, lift_coefficient)
    return AeroCoefficients(
        lift_coefficient=lift_coefficient,
        drag_coefficient=drag_coefficient,
        skin_friction_coefficient=skin_friction_coefficient,
        pressure_drag_coefficient=pressure_drag_coefficient,
        lift_newtons=lift,
        drag_newtons=drag,
        skin_friction_drag_newtons=skin_friction_drag,
        pressure_drag_newtons=pressure_drag,
        effective_angle_degrees=effective_angle,
        dynamic_pressure_pascals=dynamic_pressure,
        reference_area_m2=reference_area,
        frontal_area_m2=frontal_area,
        wetted_area_m2=wetted,
        reynolds_number=reynolds,
        flow_regime=flow_regime(reynolds),
        laminar_boundary_layer_m=laminar_boundary_layer,
        turbulent_boundary_layer_m=turbulent_boundary_layer,
        circulation_m2_s=circulation,
        lift_per_span_newtons_per_m=settings.air_density * settings.wind_speed * circulation,
    )


def drag_force(settings: AirfoilSettings, drag_coefficient: float, dynamic_pressure: Optional[float] = None) -> float:
    q = dynamic_pressure
    if q is None:
        q = 0.5 * settings.air_density * settings.wind_speed * settings.wind_speed
    return q * frontal_area_m2(settings) * drag_coefficient


def reference_area_m2(settings: AirfoilSettings) -> float:
    if settings.reference_area is not None:
        return max(settings.reference_area, 1e-9)
    return max(settings.chord * settings.span, 1e-9)


def frontal_area_m2(settings: AirfoilSettings) -> float:
    if settings.frontal_area is not None:
        return max(settings.frontal_area, 1e-9)
    return max(settings.body_width * settings.body_height, 1e-9)


def wetted_area_m2(settings: AirfoilSettings) -> float:
    if settings.wetted_area is not None:
        return max(settings.wetted_area, 1e-9)
    length = max(settings.body_length, 1e-9)
    width = max(settings.body_width, 1e-9)
    height = max(settings.body_height, 1e-9)
    return 2.0 * (length * width + length * height + width * height)


def average_skin_friction_coefficient(reynolds: float) -> float:
    if reynolds <= 0.0:
        return 0.0
    laminar = 1.328 / np.sqrt(reynolds)
    turbulent = 0.074 / reynolds**0.2
    if reynolds < 5.0e5:
        return float(laminar)
    if reynolds > 3.0e6:
        return float(turbulent)
    blend = (reynolds - 5.0e5) / (2.5e6)
    return float((1.0 - blend) * laminar + blend * turbulent)


def pressure_drag_coefficient_estimate(
    settings: AirfoilSettings,
    lift_coefficient: float,
    flap_drag_delta: float,
) -> float:
    bluntness = frontal_area_m2(settings) / max(reference_area_m2(settings), 1e-9)
    if not is_wing_model(settings):
        return float(0.18 + 0.72 * bluntness)

    alpha = abs(np.radians(settings.angle_of_attack_degrees))
    thickness_drag = 0.22 * settings.thickness_ratio * settings.thickness_ratio
    separation_drag = 0.85 * alpha * alpha
    induced_drag = 0.035 * lift_coefficient * lift_coefficient
    form_drag = 0.035 + 0.18 * bluntness
    return float(form_drag + thickness_drag + separation_drag + induced_drag + flap_drag_delta)


def is_wing_model(settings: AirfoilSettings) -> bool:
    return settings.shape_model == "wing"


def reynolds_number(settings: AirfoilSettings) -> float:
    viscosity = max(settings.dynamic_viscosity, 1e-12)
    return settings.air_density * abs(settings.wind_speed) * settings.chord / viscosity


def flow_regime(reynolds: float) -> str:
    if reynolds < 5.0e5:
        return "laminar"
    if reynolds < 3.0e6:
        return "transitional"
    return "turbulent"


def circulation_from_lift_coefficient(settings: AirfoilSettings, lift_coefficient: float) -> float:
    # From Kutta-Joukowski: L' = rho * V * Gamma, matched to L' = q * c * CL.
    return 0.5 * settings.wind_speed * settings.chord * lift_coefficient


def boundary_layer_thickness(settings: AirfoilSettings, reynolds: Optional[float] = None) -> tuple[float, float]:
    re_chord = reynolds_number(settings) if reynolds is None else reynolds
    if re_chord <= 0.0:
        return 0.0, 0.0

    chord = max(settings.chord, 0.0)
    laminar = 5.0 * chord / np.sqrt(re_chord)
    turbulent = 0.37 * chord / re_chord**0.2
    return float(laminar), float(turbulent)


def airfoil_outline(settings: AirfoilSettings, points: int = 180) -> tuple[np.ndarray, np.ndarray]:
    x = np.linspace(0.0, settings.chord, points)
    chord_x = x / settings.chord
    thickness = _naca_thickness(chord_x, settings.thickness_ratio) * settings.chord
    camber = _camber_line(chord_x, settings) * settings.chord

    upper_x = x
    upper_y = camber + thickness
    lower_x = x[::-1]
    lower_y = (camber - thickness)[::-1]
    outline_x = np.concatenate([upper_x, lower_x])
    outline_y = np.concatenate([upper_y, lower_y])
    outline_x -= settings.chord * 0.5

    return rotate(outline_x, outline_y, settings.angle_of_attack_degrees)


def pressure_distribution(settings: AirfoilSettings, points: int = 180) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(0.02, 0.98, points)
    camber_delta, angle_delta, _drag_delta = wing_adjustment(settings)
    alpha = np.radians(settings.angle_of_attack_degrees + angle_delta)
    camber = settings.camber + camber_delta

    suction_peak = 1.35 * alpha + 2.4 * camber
    leading_edge = np.exp(-4.2 * x)
    recovery = 0.25 * (1.0 - x)
    upper_cp = 0.18 - suction_peak * leading_edge - 0.18 * np.sin(np.pi * x)
    lower_cp = 0.10 + 0.48 * alpha * leading_edge + recovery * camber
    return x, upper_cp, lower_cp


def flow_field(
    settings: AirfoilSettings,
    x_points: int = 88,
    y_points: int = 58,
) -> dict[str, np.ndarray]:
    x = np.linspace(-1.0, 1.7, x_points) * settings.chord
    y = np.linspace(-0.75, 0.75, y_points) * settings.chord
    xx, yy = np.meshgrid(x, y)

    local_x, local_y = rotate(xx, yy, -settings.angle_of_attack_degrees)
    radius = settings.chord * 0.5
    r = np.maximum(np.hypot(local_x, local_y), radius)
    theta = np.arctan2(local_y, local_x)
    mask = r <= radius

    coeffs = estimate_coefficients(settings)
    circulation = coeffs.circulation_m2_s

    radial_velocity = settings.wind_speed * (1.0 - (radius * radius) / (r * r)) * np.cos(theta)
    tangential_velocity = (
        -settings.wind_speed * (1.0 + (radius * radius) / (r * r)) * np.sin(theta)
        + circulation / (2.0 * np.pi * r)
    )
    local_u = radial_velocity * np.cos(theta) - tangential_velocity * np.sin(theta)
    local_v = radial_velocity * np.sin(theta) + tangential_velocity * np.cos(theta)
    u, v = rotate(local_u, local_v, settings.angle_of_attack_degrees)

    speed = np.hypot(u, v)
    cp = 1.0 - (speed / max(settings.wind_speed, 1e-6)) ** 2
    u = np.where(mask, np.nan, u)
    v = np.where(mask, np.nan, v)
    speed = np.where(mask, np.nan, speed)
    cp = np.where(mask, np.nan, cp)
    return {"x": xx, "y": yy, "u": u, "v": v, "speed": speed, "cp": cp, "mask": mask}


def streamline_paths(
    field: dict[str, np.ndarray],
    seeds: int = 24,
    steps: int = 240,
    step_size: float = 0.018,
) -> list[tuple[np.ndarray, np.ndarray]]:
    x_grid = field["x"][0]
    y_grid = field["y"][:, 0]
    y_seeds = np.linspace(y_grid.min() * 0.86, y_grid.max() * 0.86, seeds)
    paths: list[tuple[np.ndarray, np.ndarray]] = []

    for seed_y in y_seeds:
        xs = [float(x_grid.min())]
        ys = [float(seed_y)]
        for _step in range(steps):
            u = _sample(field["u"], x_grid, y_grid, xs[-1], ys[-1])
            v = _sample(field["v"], x_grid, y_grid, xs[-1], ys[-1])
            if not np.isfinite(u) or not np.isfinite(v):
                break
            speed = max(float(np.hypot(u, v)), 1e-6)
            xs.append(xs[-1] + step_size * u / speed)
            ys.append(ys[-1] + step_size * v / speed)
            if xs[-1] > x_grid.max() or ys[-1] < y_grid.min() or ys[-1] > y_grid.max():
                break
        if len(xs) > 5:
            paths.append((np.array(xs), np.array(ys)))
    return paths


def rotate(x: np.ndarray, y: np.ndarray, degrees: float) -> tuple[np.ndarray, np.ndarray]:
    angle = np.radians(degrees)
    cos_a = np.cos(angle)
    sin_a = np.sin(angle)
    return x * cos_a - y * sin_a, x * sin_a + y * cos_a


def _naca_thickness(x: np.ndarray, thickness_ratio: float) -> np.ndarray:
    return 5.0 * thickness_ratio * (
        0.2969 * np.sqrt(np.maximum(x, 0.0))
        - 0.1260 * x
        - 0.3516 * x * x
        + 0.2843 * x**3
        - 0.1015 * x**4
    )


def _camber_line(x: np.ndarray, settings: AirfoilSettings) -> np.ndarray:
    camber_delta, _angle_delta, _drag_delta = wing_adjustment(settings)
    camber = settings.camber + camber_delta
    return camber * np.sin(np.pi * x) ** 1.25


def _sample(values: np.ndarray, x_grid: np.ndarray, y_grid: np.ndarray, x: float, y: float) -> float:
    if x < x_grid.min() or x > x_grid.max() or y < y_grid.min() or y > y_grid.max():
        return float("nan")
    xi = int(np.searchsorted(x_grid, x) - 1)
    yi = int(np.searchsorted(y_grid, y) - 1)
    xi = int(np.clip(xi, 0, len(x_grid) - 2))
    yi = int(np.clip(yi, 0, len(y_grid) - 2))

    x0 = x_grid[xi]
    x1 = x_grid[xi + 1]
    y0 = y_grid[yi]
    y1 = y_grid[yi + 1]
    tx = (x - x0) / max(x1 - x0, 1e-12)
    ty = (y - y0) / max(y1 - y0, 1e-12)

    q00 = values[yi, xi]
    q10 = values[yi, xi + 1]
    q01 = values[yi + 1, xi]
    q11 = values[yi + 1, xi + 1]
    return float(
        q00 * (1.0 - tx) * (1.0 - ty)
        + q10 * tx * (1.0 - ty)
        + q01 * (1.0 - tx) * ty
        + q11 * tx * ty
    )
