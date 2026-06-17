@echo off
setlocal

set "REPO_ROOT=%~dp0"
set "PYTHON=%REPO_ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Virtual environment not found at .venv
  echo Create it with: python -m venv .venv
  echo Then install dependencies with: .\.venv\Scripts\python.exe -m pip install -e .
  exit /b 1
)

cd /d "%REPO_ROOT%"
"%PYTHON%" -m streamlit run aero_lab/streamlit_app.py
