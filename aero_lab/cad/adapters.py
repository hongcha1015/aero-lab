from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_CAD_EXTENSIONS = {".stl", ".obj", ".step", ".stp", ".glb", ".gltf"}


@dataclass(frozen=True)
class CadImportRequest:
    path: Path
    units: str = "m"
    target_chord: float | None = None


def supported_cad_extensions() -> tuple[str, ...]:
    return tuple(sorted(SUPPORTED_CAD_EXTENSIONS))


def validate_cad_import(request: CadImportRequest) -> None:
    extension = request.path.suffix.lower()
    if extension not in SUPPORTED_CAD_EXTENSIONS:
        allowed = ", ".join(supported_cad_extensions())
        raise ValueError(f"Unsupported CAD extension {extension!r}. Expected one of: {allowed}.")


def load_cad_mesh_placeholder(request: CadImportRequest) -> None:
    """Reserved for future 3D visualization.

    Suggested implementation path:
    1. Parse STL/OBJ/GLTF locally for mesh display.
    2. Use STEP/STP through a CAD kernel such as pythonocc-core when available.
    3. Normalize the mesh to the selected chord/reference dimensions.
    4. Send vertices/faces to a Three.js or Plotly 3D viewer.
    """
    validate_cad_import(request)
    raise NotImplementedError("CAD mesh import is reserved for the future 3D visual testing path.")
