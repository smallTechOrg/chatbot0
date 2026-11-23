"""Logging: one setup that is safe to repeat, and no print() left in the app code."""

import ast
import logging
import subprocess
from pathlib import Path

from core.logging import configure_logging

ROOT = Path(__file__).resolve().parents[2]
# core/config.py prints one startup line before logging exists; the legacy chatbot0/ package goes with the Next.js move.
ALLOWED = {"core/config.py", "chatbot0/__init__.py"}


def test_configure_logging_is_idempotent(monkeypatch):
    root = logging.getLogger()
    before = len(root.handlers)
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging()
    configure_logging()
    ours = [h for h in root.handlers if getattr(h, "_chatbot0", False)]
    assert len(ours) == 1
    assert len(root.handlers) <= before + 1
    assert root.level == logging.DEBUG
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    configure_logging()
    assert root.level == logging.INFO


def test_app_code_does_not_print():
    files = subprocess.check_output(["git", "ls-files", "*.py"], cwd=ROOT, text=True).split()
    offenders = []
    for name in files:
        if name.startswith("test/") or name in ALLOWED:
            continue
        for node in ast.walk(ast.parse((ROOT / name).read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
                offenders.append(f"{name}:{node.lineno}")
    assert not offenders, f"use logging, not print: {offenders}"
