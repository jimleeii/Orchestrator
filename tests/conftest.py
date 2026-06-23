import sys
import os

# Ensure the repository root is first on sys.path so tests import the workspace
# local modules (for example `scripts` and `src`) instead of installed packages.
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
