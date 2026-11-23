"""Filesystem locations the app reads from, anchored on the repository root, never on the working directory."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT / "prompts"
