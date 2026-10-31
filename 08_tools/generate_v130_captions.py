"""Compatibility entry for the PUBLIC caption generator; no private lyrics."""
from pathlib import Path
import runpy
runpy.run_path(str(Path(__file__).resolve().parents[1]/"tools/generate_public_captions.py"),run_name="__main__")
