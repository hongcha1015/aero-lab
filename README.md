# Aero Lab

Aero Lab is a local aerodynamics sandbox for experimenting with simple vehicle and wing flow models. It combines a Streamlit control surface, Plotly graph pages, and a browser-rendered React canvas preview for live flow visualization.

The project is currently focused on building a clear force-calculation pipeline before adding custom shape imports. The default app mode treats the center object as a simple body, not a wing, so it does not apply angle-of-attack lift or front/rear wing flap effects. Wing-style calculations still exist behind `shape_model="wing"` for later development.

## Current Features

- Streamlit dashboard with separate `Live Tunnel` and `Graphs` pages.
- React/HTML canvas flow preview embedded in Streamlit, with direct local HTML fallback for quick inspection.
- Simple body force model with explicit dimensions:
  - chord
  - span
  - body length
  - body width
  - body height
  - derived reference, frontal, and wetted areas
- Drag split into skin-friction drag and pressure/form drag.
- Reynolds number, laminar/transitional/turbulent regime estimate, dynamic pressure, and boundary-layer thickness estimates.
- Potential-flow-style field approximation for graphing streamlines and pressure coefficient fields.
- Locked in-development controls for angle of attack and front/rear wing flap degrees.

The app is split into:

- `aero_lab.streamlit_app`: Streamlit layout, controls, metrics, live page, and graph page.
- `aero_lab.frontend`: React/HTML canvas component embedded in Streamlit for live particle flow.
- `aero_lab.calc`: Numpy aerodynamic approximations for force estimates, Reynolds/regime calculations, flow fields, streamlines, and pressure distribution.
- `aero_lab.cad`: placeholders for future CAD mesh import and 3D visualization testing.

## Setup

```powershell
python -m venv .venv
.\.venv\bin\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Some Windows Python installs create `.venv\Scripts` instead of `.venv\bin`. If so, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
```

If pip tries to compile Numpy from source on Windows, use a standard CPython install from python.org or the Microsoft Store for this venv. The dashboard expects normal binary wheels for `numpy`, `plotly`, and `streamlit`. Python 3.14 currently uses Numpy 2.x wheels, so the project allows both Numpy 1.x and 2.x.

## Run

```powershell
python -m streamlit run aero_lab/streamlit_app.py
```

Or, after editable install:

```powershell
aero-lab
```

## Extension Points

Simple body and wing behavior are separated through `AirfoilSettings.shape_model`.

- `shape_model="simple_body"` ignores wing lift, circulation, and front/rear flap adjustments.
- `shape_model="wing"` enables the current placeholder airfoil lift and wing adjustment formulas.

Approximate front/rear wing effects are centralized in `aero_lab.calc.airfoil.wing_adjustment()`. Replace that function when empirical, wind tunnel, CFD-derived, or panel-method relationships are available.

Area helpers in `aero_lab.calc.airfoil` are intended to become the bridge to custom geometry:

- `reference_area_m2()`
- `frontal_area_m2()`
- `wetted_area_m2()`

Imported or user-drawn shapes should eventually provide these values directly instead of relying on box-style dimension estimates.

Future CAD import hooks are in `aero_lab.cad.adapters`. The intended path is to load STL/OBJ/GLTF directly for mesh display, and STEP/STP later through a CAD kernel such as `pythonocc-core`.

## Test

```powershell
python -m unittest discover -s tests
```

## Project Structure

```text
aero_lab/
  main.py
  streamlit_app.py
  cad/
    adapters.py
  calc/
    airfoil.py
  frontend/
    canvas_component.py
    wind_tunnel_component.html
tests/
  test_airfoil.py
```

## Future Planned Implementations

```text
- Test asymmetric custom shapes, especially curved airfoil/body profiles
- Add 2D side-view shape editing with derived frontal, wetted, and reference areas
- Replace the circular potential-flow proxy with a source/vortex panel method
- Support imported shape geometry for simple 2D calculations
- Re-enable and refine angle-of-attack and front/rear wing controls once formulas are stable
- Add empirical or lookup-table support for race-car wing and body coefficients
- Add CAD imports and 3D testing support through STL/OBJ/GLTF first, then STEP/STP later
- Build a 3D visualization path while preserving the current force-breakdown API
```

```text
Developed with the help of Codex
```
