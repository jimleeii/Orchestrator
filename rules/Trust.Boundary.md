# Trust Boundary Policy for Script Execution

## Purpose

Define boundaries for script execution to reduce operational and security risk when the Orchestrator runs scripts via `run_skill_script()` and `run_script()`.

## Threat Model

- **Scenario 1**: Malicious or corrupted script path injection via user input or external source
- **Scenario 2**: Path traversal or escape attempts (e.g., `../../../etc/passwd`)
- **Scenario 3**: Execution of scripts from untrusted locations (e.g., `/tmp`, `/var/tmp`, user desktop)
- **Scenario 4**: Symlink attacks or TOCTOU races on script paths

## Trust Boundaries

### Allowed Script Locations (Allowlist)

Scripts may be executed from **only** the following repository-relative paths:

1. **Skills directory**: `skills/<skill_name>/` (primary use case via `run_skill_script()`)
2. **Scripts directory**: `scripts/` (internal orchestration helpers)
3. **Test scripts directory**: `test-scripts/` (for development and CI validation)

### Blocked Script Locations (Deny)

Scripts **must NOT** be executed from:

- System paths (`/bin`, `/usr/bin`, `/usr/local/bin`, etc. on Unix; `C:\Windows`, `C:\Program Files`, etc. on Windows)
- User home directories (`~`, `$HOME`, `%USERPROFILE%`, etc.)
- Temporary directories (`/tmp`, `/var/tmp`, `C:\Temp`, etc.)
- Absolute paths outside the repository root
- Network-mounted or non-existent paths

## Validation Logic

When `run_script(path)` is invoked:

1. **Normalize** the path: resolve `.` and `..`, remove trailing slashes, canonicalize to absolute form
2. **Resolve repo root**: find the repository root via `.git` (or `orchestrator_root` environment variable if set)
3. **Check allowlist**:
   - If the normalized path starts with `repo_root/skills/`, `repo_root/scripts/`, or `repo_root/test-scripts/`, permit execution
   - Otherwise, **deny** execution and return an error message
4. **Reject symlinks** (optional but recommended): if the system is vulnerable to symlink attacks, reject symlinks pointing outside the allowlist

## Implementation

### Python Implementation Pattern

```python
import os
from pathlib import Path

def validate_script_path(script_path: str) -> tuple[bool, str]:
    """Validate that script_path is within allowed repository locations.
    
    Returns:
        (is_valid, reason_or_error_msg)
    """
    # Normalize and resolve to absolute path
    try:
        abs_path = Path(script_path).resolve()
    except (OSError, ValueError) as e:
        return False, f"Invalid path: {e}"
    
    # Find repo root (via .git or env var)
    repo_root_env = os.environ.get("ORCHESTRATOR_REPO_ROOT")
    if repo_root_env:
        repo_root = Path(repo_root_env).resolve()
    else:
        # Walk up from script_path looking for .git
        current = abs_path.parent if abs_path.is_file() else abs_path
        repo_root = None
        for ancestor in [current] + list(current.parents):
            if (ancestor / ".git").exists():
                repo_root = ancestor
                break
        if not repo_root:
            return False, "Repository root not found (.git not detected)"
    
    # Check if path is within allowlist
    allowed_dirs = [
        repo_root / "skills",
        repo_root / "scripts",
        repo_root / "test-scripts",
    ]
    
    for allowed_dir in allowed_dirs:
        if abs_path.is_relative_to(allowed_dir):
            return True, ""
    
    return False, f"Script path outside allowed locations: {abs_path}"
```

### PowerShell Implementation Pattern

```powershell
function Test-ScriptPath {
    param (
        [string]$ScriptPath
    )
    
    # Normalize path
    $AbsPath = (Resolve-Path $ScriptPath -ErrorAction Stop).Path
    
    # Find repo root
    $RepoRoot = $env:ORCHESTRATOR_REPO_ROOT
    if (-not $RepoRoot) {
        $Current = Split-Path $AbsPath
        while ($Current) {
            if (Test-Path "$Current\.git") {
                $RepoRoot = $Current
                break
            }
            $Current = Split-Path $Current
        }
    }
    
    if (-not $RepoRoot) {
        return @{ Valid = $false; Reason = "Repository root not found" }
    }
    
    # Check allowlist
    $AllowedDirs = @(
        "$RepoRoot\skills",
        "$RepoRoot\scripts",
        "$RepoRoot\test-scripts"
    )
    
    foreach ($Dir in $AllowedDirs) {
        if ($AbsPath.StartsWith((Resolve-Path $Dir).Path)) {
            return @{ Valid = $true; Reason = "" }
        }
    }
    
    return @{ Valid = $false; Reason = "Script path outside allowed locations: $AbsPath" }
}
```

## Configuration

### Environment Variables

- `ORCHESTRATOR_REPO_ROOT`: Optional override for repository root detection (defaults to `.git` search)
- `ORCHESTRATOR_TRUST_MODE`: Optional explicit mode control:
  - `"strict"` (default): Enforce allowlist rigorously
  - `"permissive"`: Log warnings but allow execution (not recommended for production)
  - `"strict-no-symlinks"`: Strict + reject symlinks

### Activation

Add validation to `run_script()` function before execution:

```python
def run_script(path: str, args: Optional[List[str]] = None, timeout: int = 30) -> str:
    """Run a script file with trust-boundary validation."""
    # Validate path against allowlist
    is_valid, reason = validate_script_path(path)
    if not is_valid:
        trust_mode = os.environ.get("ORCHESTRATOR_TRUST_MODE", "strict")
        if trust_mode in ("strict", "strict-no-symlinks"):
            return f"Script execution blocked: {reason}"
        elif trust_mode == "permissive":
            print(f"WARNING: {reason}", file=sys.stderr)
        # else: fall through and log warning
    
    # ... rest of script execution ...
```

## Exceptions and Explicit Trusted Mode

For CI/CD pipelines or special workflows that need to run scripts outside the standard allowlist:

1. Set `ORCHESTRATOR_TRUST_MODE=permissive` in the CI environment
2. Document the exception with rationale in the CI configuration
3. Log all permissive-mode executions to an audit trail (optional but recommended)
4. Review permissive-mode logs periodically for anomalies

## Testing

Tests MUST validate:

1. ✓ Allowed paths (within `skills/`, `scripts/`, `test-scripts/`) execute successfully
2. ✓ Blocked absolute paths outside the repository are rejected
3. ✓ Path traversal attempts (e.g., `scripts/../../../etc/passwd`) are rejected
4. ✓ User home directory paths are rejected
5. ✓ Temporary directory paths are rejected
6. ✓ Relative paths that resolve outside the allowlist are rejected
7. ✓ Symlink resolution behavior is as documented (if strict-no-symlinks mode is implemented)

See `hooks/test_trust_boundary.py` for comprehensive test coverage.

## Migration and Rollout

1. **Phase 1**: Implement validation logic, run in `permissive` mode by default to gather baseline
2. **Phase 2**: After 1-2 weeks of `permissive` logging, switch to `strict` mode as default
3. **Phase 3**: Monitor for anomalies; escalate any false positives to policy review

## Backwards Compatibility

- Existing uses of `run_skill_script()` and `run_script()` within `skills/`, `scripts/`, and `test-scripts/` require **no changes**.
- Legacy calls from outside those directories will see warnings in `permissive` mode or failures in `strict` mode.

## Related Policies

- `Placeholder.Validation.md` — Validates template tokens in append-capable logging commands
- `Logging.Policy.md` — Defines logging level semantics
