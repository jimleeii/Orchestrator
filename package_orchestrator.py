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


def main(argv=None):
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
    # include 'prompts' and 'knowledge' so static prompt templates and generated
    # knowledge pages are available in packaged agents when present.
    dirs = ['hooks', 'templates', 'skills', 'src', 'scripts', 'prompts', 'knowledge']

    for f in files:
        src = os.path.join(source_root, f)
        if not os.path.isfile(src) and source_root != repo_root:
            # fallback to repo root if the file is not present in the agent subfolder
            src = os.path.join(repo_root, f)
        if os.path.isfile(src):
            shutil.copy2(src, os.path.join(dest, os.path.basename(f)))

    for d in dirs:
        # Prefer the agent-specific directory (under .github/agents/Orchestrator) but
        # also merge in files from the repository root when present. This ensures
        # files like templates/config.json that may only live at the repo root are
        # included even when an agent subfolder exists.
        src_agent = os.path.join(source_root, d)
        src_repo = os.path.join(repo_root, d)
        dst = os.path.join(dest, d)

        # If an agent-specific directory exists, copy it first.
        if os.path.isdir(src_agent):
            shutil.copytree(src_agent, dst, dirs_exist_ok=True, ignore=IGNORE_PATTERNS)

            # If the repo also has the same directory, copy any files that are
            # missing from the staged destination (do not overwrite).
            if os.path.isdir(src_repo):
                for root_dir, dirnames, filenames in os.walk(src_repo):
                    # Skip __pycache__ directories
                    dirnames[:] = [dn for dn in dirnames if dn != '__pycache__']
                    rel = os.path.relpath(root_dir, src_repo)
                    target_dir = os.path.join(dst, rel) if rel != '.' else dst
                    os.makedirs(target_dir, exist_ok=True)
                    for fn in filenames:
                        # Apply basic ignore rules (mirror IGNORE_PATTERNS)
                        if fn.endswith(('.pyc', '.pyo')):
                            continue
                        if fn.startswith('test_') and fn.endswith('.py'):
                            continue
                        src_file = os.path.join(root_dir, fn)
                        dest_file = os.path.join(target_dir, fn)
                        if not os.path.exists(dest_file):
                            try:
                                shutil.copy2(src_file, dest_file)
                            except Exception:
                                # Non-fatal: continue copying other files
                                pass
        else:
            # Fallback to repository root when agent-specific directory is absent
            if os.path.isdir(src_repo):
                dst = os.path.join(dest, d)
                shutil.copytree(src_repo, dst, dirs_exist_ok=True, ignore=IGNORE_PATTERNS)

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


if __name__ == '__main__':
    main()
