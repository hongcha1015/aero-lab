# Aero Lab

A local aerodynamics sandbox focused on a Streamlit control surface with a browser-rendered 2D flow display.

The app is split into:

- `aero_lab.streamlit_app`: Streamlit layout, controls, metrics, and Plotly tabs.
- `aero_lab.frontend`: React/HTML canvas component embedded in Streamlit for live particle flow.
- `aero_lab.calc`: Numpy airfoil approximations for lift, drag, streamlines, and pressure distribution.
- `aero_lab.cad`: placeholders for future CAD mesh import and 3D visualization testing.

The current model uses a generic F1-style airfoil approximation with adjustable wind speed, angle of attack, front wing flap degrees, and rear wing flap degrees.

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

Approximate front/rear wing effects are centralized in `aero_lab.calc.airfoil.wing_adjustment()`. Replace that function when you have empirical, wind tunnel, or CFD-derived relationships.

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

## TODO

```text
- Update approximate calculation models for front/rear wing adjustment for F1 mode
- Implement 2D shape/sideview slices for user-created shapes
- Implement CAD imports and 3D testing support
```
