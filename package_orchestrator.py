#!/usr/bin/env python3
"""Create Orchestrator.zip containing the agent files (top-level folder: Orchestrator).

Includes: orchestrator.agent.md, orchestrator-tools.md, requirements.txt 
and directories: prompts, templates, skills, src, scripts.
Excludes cache artifacts such as __pycache__ and compiled Python files.
"""
import os
import shutil
import tempfile
import sys

IGNORE_PATTERNS = shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo')

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
staging = tempfile.mkdtemp(prefix="orch_pkg_")
dest = os.path.join(staging, "Orchestrator")
os.makedirs(dest, exist_ok=True)

files = [
    'orchestrator.agent.md', 'orchestrator-tools.md', 'requirements.txt'
]
dirs = ['prompts', 'templates', 'skills', 'src', 'scripts']

for f in files:
    src = os.path.join(repo_root, f)
    if os.path.isfile(src):
        shutil.copy2(src, os.path.join(dest, os.path.basename(f)))

for d in dirs:
    srcd = os.path.join(repo_root, d)
    if os.path.isdir(srcd):
        dst = os.path.join(dest, d)
        shutil.copytree(srcd, dst, dirs_exist_ok=True, ignore=IGNORE_PATTERNS)

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
