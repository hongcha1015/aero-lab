from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from aero_lab.calc.airfoil import AeroCoefficients, AirfoilSettings


TEMPLATE_PATH = Path(__file__).with_name("wind_tunnel_component.html")
VENDOR_PATH = Path(__file__).with_name("vendor")


def render_canvas_html(settings: AirfoilSettings, coefficients: AeroCoefficients) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    template = template.replace(
        '<script src="vendor/react.production.min.js"></script>',
        '<script>window.React = null;</script>',
    )
    template = template.replace(
        '<script src="vendor/react-dom.production.min.js"></script>',
        '<script>window.ReactDOM = null;</script>',
    )
    payload: dict[str, Any] = {
        "settings": asdict(settings),
        "coefficients": asdict(coefficients),
    }
    config = json.dumps(payload, separators=(",", ":"))
    return template.replace("const INJECTED_CONFIG = null;", f"const INJECTED_CONFIG = {config};")
