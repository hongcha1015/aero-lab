from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AirfoilSettings:
    wind_speed: float = 45.0
    angle_of_attack_degrees: float = 6.0
    front_wing_degrees: float = 0.0
    rear_wing_degrees: float = 0.0
    chord: float = 1.0
    thickness_ratio: float = 0.12
    camber: float = 0.035
    air_density: float = 1.225
    reference_area: float = 1.0


@dataclass(frozen=True)
class AeroCoefficients:
    lift_coefficient: float
    drag_coefficient: float
    lift_newtons: float
    drag_newtons: float
    effective_angle_degrees: float


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
    camber_delta, angle_delta, drag_delta = wing_adjustment(settings)
    effective_angle = settings.angle_of_attack_degrees + angle_delta
    alpha = np.radians(effective_angle)
    effective_camber = settings.camber + camber_delta

    lift_coefficient = 2.0 * np.pi * (alpha + effective_camber)
    lift_coefficient = float(np.clip(lift_coefficient, -3.2, 3.2))

    induced_drag = 0.035 * lift_coefficient * lift_coefficient
    profile_drag = 0.018 + 0.72 * settings.thickness_ratio * settings.thickness_ratio
    drag_coefficient = float(profile_drag + induced_drag + drag_delta)

    dynamic_pressure = 0.5 * settings.air_density * settings.wind_speed * settings.wind_speed
    lift = dynamic_pressure * settings.reference_area * lift_coefficient
    drag = dynamic_pressure * settings.reference_area * drag_coefficient
    return AeroCoefficients(
        lift_coefficient=lift_coefficient,
        drag_coefficient=drag_coefficient,
        lift_newtons=lift,
        drag_newtons=drag,
        effective_angle_degrees=effective_angle,
    )


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
    semi_major = settings.chord * 0.52
    semi_minor = settings.chord * max(0.055, settings.thickness_ratio * 0.70)
    ellipse_radius = (local_x / semi_major) ** 2 + (local_y / semi_minor) ** 2
    mask = ellipse_radius <= 1.0

    wind_u = np.full_like(xx, settings.wind_speed)
    wind_v = np.zeros_like(yy)

    safe_radius = np.maximum(ellipse_radius, 1.0)
    influence = 1.0 / (safe_radius * safe_radius)
    normal_x = local_x / (semi_major * semi_major)
    normal_y = local_y / (semi_minor * semi_minor)
    normal_length = np.maximum(np.hypot(normal_x, normal_y), 1e-6)
    normal_x /= normal_length
    normal_y /= normal_length
    world_nx, world_ny = rotate(normal_x, normal_y, settings.angle_of_attack_degrees)

    blockage = settings.wind_speed * 0.85 * influence
    u = wind_u - blockage * world_nx
    v = wind_v - blockage * world_ny

    camber_delta, angle_delta, _drag_delta = wing_adjustment(settings)
    circulation = settings.wind_speed * settings.chord * (
        np.radians(settings.angle_of_attack_degrees + angle_delta) + settings.camber + camber_delta
    )
    radius_squared = np.maximum(xx * xx + yy * yy, 0.015)
    u += -yy * circulation / (2.0 * np.pi * radius_squared)
    v += xx * circulation / (2.0 * np.pi * radius_squared)

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
