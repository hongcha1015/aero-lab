from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        from streamlit.web import cli as streamlit_cli
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Streamlit is not installed. Activate the venv, then run: "
            'python -m pip install -e "."'
        ) from exc

    app_path = Path(__file__).with_name("streamlit_app.py")
    sys.argv = ["streamlit", "run", str(app_path)]
    streamlit_cli.main()
