"""
Root conftest.py — path bootstrapping.

The top-level resilio/ directory is the legacy read-only package.  All Phase 1
work lives under backend/resilio/.  The pyproject.toml [tool.pytest.ini_options]
sets pythonpath = ["backend"] and addopts = "--import-mode=importlib" so that
pytest does not inject the project root into sys.path (which would cause the
legacy resilio/ package to shadow backend/resilio/).

This file is intentionally minimal — path resolution is handled by the
pyproject.toml config.  It exists only to provide shared fixtures.
"""
