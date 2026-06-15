from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aero_lab.calc.airfoil import AeroCoefficients, AirfoilSettings


TEMPLATE_PATH = Path(__file__).with_name("wind_tunnel_component.html")


def render_canvas_html(settings: AirfoilSettings, coefficients: AeroCoefficients) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    payload: dict[str, Any] = {
        "settings": asdict(settings),
        "coefficients": asdict(coefficients),
    }
    config = json.dumps(payload, separators=(",", ":"))
    return template.replace("__CONFIG_JSON__", config)
