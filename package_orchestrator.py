#!/usr/bin/env python3
"""Create Orchestrator.zip containing the agent files (top-level folder: Orchestrator).

This script prefers packaging the agent from `.github/agents/Orchestrator` when that
directory exists (this matches how agents are distributed inside repositories). When the
folder is not present it falls back to packaging files from the repository root.

Minimum packaged artifacts (when present):
- orchestrator.agent.md (agent manifest)
- orchestrator-tools.md (tools list)
- requirements.txt (dependencies)
- optional docs: DISPATCH_AND_LOGGING_API.md, HEALTH_METADATA.md, OPERATIONAL_TRUTH.md
- hook configuration: log_cycle.json, rtk-rewrite.json
- directories: hooks, templates, skills, src, scripts

Excludes cache artifacts and test files.
"""
import os
import shutil
import tempfile
import sys

IGNORE_PATTERNS = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo', 'test_*.py')

def _find_repo_root(start_dir: str) -> str:
    # Walk up until we find a repository marker and return that directory.
    # Prefer project-specific markers over an external AGENTS.md file which
    # may not exist in all environments.
    d = os.path.abspath(start_dir)
    markers = ('orchestrator.agent.md', '.git', '.github')
    while True:
        for m in markers:
            if os.path.exists(os.path.join(d, m)):
                return d
        parent = os.path.abspath(os.path.join(d, '..'))
        if parent == d:
            return start_dir
        d = parent

script_dir = os.path.abspath(os.path.dirname(__file__))
repo_root = _find_repo_root(script_dir)

# Prefer packaged agent under .github/agents/Orchestrator when present
agent_candidate = os.path.join(repo_root, '.github', 'agents', 'Orchestrator')
source_root = agent_candidate if os.path.isdir(agent_candidate) else repo_root

staging = tempfile.mkdtemp(prefix="orch_pkg_")
dest = os.path.join(staging, "Orchestrator")
os.makedirs(dest, exist_ok=True)

# Minimum file set (optional files will be copied when present)
files = [
    'orchestrator.agent.md',
    'orchestrator-tools.md',
    'requirements.txt',
    'DISPATCH_AND_LOGGING_API.md',
    'HEALTH_METADATA.md',
    'OPERATIONAL_TRUTH.md',
    'log_cycle.json',
    'rtk-rewrite.json',
]

# Directories to include in the packaged agent
dirs = ['hooks', 'templates', 'skills', 'src', 'scripts']

for f in files:
    src = os.path.join(source_root, f)
    if not os.path.isfile(src) and source_root != repo_root:
        # fallback to repo root if the file is not present in the agent subfolder
        src = os.path.join(repo_root, f)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(dest, os.path.basename(f)))

for d in dirs:
    srcd = os.path.join(source_root, d)
    if not os.path.isdir(srcd) and source_root != repo_root:
        srcd = os.path.join(repo_root, d)
    if os.path.isdir(srcd):
        dst = os.path.join(dest, d)
        shutil.copytree(srcd, dst, dirs_exist_ok=True, ignore=IGNORE_PATTERNS)

# Defensive cleanup: remove test files and test directories from the staged package
for root, dirnames, filenames in os.walk(dest):
    for fn in list(filenames):
        if fn.startswith('test_') and fn.endswith('.py'):
            try:
                os.remove(os.path.join(root, fn))
            except Exception:
                pass
    for dn in list(dirnames):
        if dn.lower() == 'tests' or dn.startswith('test_'):
            try:
                shutil.rmtree(os.path.join(root, dn), ignore_errors=True)
            except Exception:
                pass

zip_path = os.path.join(repo_root, 'Orchestrator.zip')
if os.path.exists(zip_path):
    try:
        os.remove(zip_path)
    except Exception as e:
        print('Failed to remove existing zip:', e, file=sys.stderr)

base_name = os.path.splitext(zip_path)[0]
shutil.make_archive(base_name, 'zip', root_dir=staging, base_dir='Orchestrator')
print('WROTE_ZIP:', zip_path)
print('SIZE:', os.path.getsize(zip_path))

# cleanup
try:
    shutil.rmtree(staging)
except Exception:
    pass

print('Done')
