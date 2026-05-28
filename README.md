# Orchestrator

This repository contains the Orchestrator agent: a coordinator that manages specialized subagents and persists activity to a wiki-backed log.

Build and install locally:

```bash
# (recommended) create and activate a virtual environment first:
# python -m venv .venv && .\.venv\Scripts\activate

# Install developer tooling (build, twine, wheel, etc.) and test/linters
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

# Build wheel and sdist
python -m build

# Install the built wheel
python -m pip install dist/orchestrator-0.1.0-py3-none-any.whl
```

CLI entry points installed:

- `orchestrator-handle-request` → wrapper around `scripts.handle_request:main`
- `orchestrator-package` → creates `Orchestrator.zip` (wraps `package_orchestrator.py`)
