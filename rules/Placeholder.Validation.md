# Placeholder Validation Policy

## Purpose

Define the policy for detecting and handling unresolved template tokens (placeholders) in append-capable logging and prompt-rendering commands.

## Scope

This policy applies to:

- `scripts/log_prompt.py` and append-capable prompt commands (`/full-log`, `/info`, `/error`, `/warning`, `/debug`, `/trace`, etc.)
- Any user-supplied text that is appended to wiki logs
- Prompt template rendering for structured evidence sections

## Token Patterns

### Valid Tokens (Must Be Resolved)

Templates use the following token formats, which **must** be resolved before appending:

1. **Environment variables**: `${ENV_NAME}` or `$ENV_NAME` (shell-style)
2. **Variable references**: `{{VAR_NAME}}` or `{VAR_NAME}` (template-style)
3. **Placeholders**: `[PLACEHOLDER]`, `<PLACEHOLDER>`, `{{TODO}}`, `[FIXME]`
4. **Cycle metadata**: `{{CYCLE_ID}}`, `{{TIMESTAMP}}`, `{{TIMESTAMP_ISO}}`

### Examples of Unresolved Tokens

```json
"submitted_request": "{{CYCLE_ID}}",  # Unresolved template var
"timestamp": "${TIMESTAMP}",           # Unresolved env var
"context": "[FILL_ME_IN]",             # Unresolved placeholder
"action": "{{TODO: implement this}}",  # Unresolved todo
"metadata": "{UNKNOWN_VAR}",           # Unresolved variable
```

## Policy Decision: Universal Validation (Strict)

**Adopted Strategy**: Universal unresolved-token checks for all append-capable commands.

When user-supplied content is about to be appended to wiki logs via `log_prompt.py`:

1. **Scan** for token patterns matching `${...}`, `{{...}}`, `{...}`, `[...]` with common placeholder names
2. **Reject** if unresolved tokens are found
3. **Return** error with list of unresolved tokens and context
4. **Allow** explicit override via `--allow-placeholders` flag (logs warning)

## Validation Logic

### Placeholder Detection Pattern

```regex
# Matches: ${VAR}, $VAR, {{VAR}}, {VAR}, [VAR], [FIXME], {{TODO}}
(?:\$\{[A-Z_][A-Z_0-9]*\}|\$[A-Z_][A-Z_0-9]*|\{\{[A-Z_][A-Z_0-9]*\}\}|\{[A-Z_][A-Z_0-9]*\}|\[[A-Z_][A-Z_0-9]*\])
```

### Common Placeholder Names (High-Confidence Unmapped Tokens)

Patterns that strongly suggest unresolved templates:

```python
UNRESOLVED_PATTERNS = [
    r"\{\{CYCLE_ID\}\}",
    r"\{\{TIMESTAMP.*\}\}",
    r"\{\{.*_ID\}\}",
    r"\{\{TODO.*\}\}",
    r"\{\{FIXME.*\}\}",
    r"\[FILL_ME_IN\]",
    r"\[PLACEHOLDER\]",
    r"\[TODO.*\]",
    r"\[FIXME.*\]",
    r"\$\{[A-Z_][A-Z_0-9]*\}",  # Unresolved shell var
]
```

### Implementation Pattern

```python
import re
from typing import Tuple, List

def check_unresolved_tokens(content: str, allow_placeholders: bool = False) -> Tuple[bool, List[str]]:
    """Check for unresolved template tokens.
    
    Args:
        content: User-supplied text to check
        allow_placeholders: If True, only warn; if False, reject
    
    Returns:
        (is_valid, list_of_unresolved_tokens_found)
    """
    unresolved_patterns = [
        r"\{\{CYCLE_ID\}\}",
        r"\{\{TIMESTAMP.*\}\}",
        r"\{\{.*_ID\}\}",
        r"\{\{TODO.*\}\}",
        r"\{\{FIXME.*\}\}",
        r"\[FILL_ME_IN\]",
        r"\[PLACEHOLDER\]",
        r"\[TODO.*\]",
        r"\[FIXME.*\]",
        r"\$\{[A-Z_][A-Z_0-9]*\}",
    ]
    
    found_tokens = []
    for pattern in unresolved_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        found_tokens.extend(matches)
    
    if not found_tokens:
        return True, []
    
    if allow_placeholders:
        # Warn but allow
        print(f"WARNING: Unresolved tokens in content: {found_tokens}", file=sys.stderr)
        return True, found_tokens
    else:
        # Reject
        return False, found_tokens
```

## Integration Points

### 1. `scripts/log_prompt.py` (Append Commands)

Before rendering and appending, validate all fields:

```python
def _validate_fields(fields: Dict[str, str], allow_placeholders: bool = False) -> Tuple[bool, List[str]]:
    """Validate all fields for unresolved tokens."""
    all_unresolved = []
    for key, value in fields.items():
        is_valid, tokens = check_unresolved_tokens(value, allow_placeholders)
        if not is_valid:
            print(f"ERROR: Field '{key}' contains unresolved tokens: {tokens}")
            return False, tokens
        all_unresolved.extend(tokens)
    return not any(all_unresolved), all_unresolved
```

### 2. `hooks/log_hooks.py` (Cycle Logging)

During `log_cycle()`, validate structured metadata:

```python
def log_cycle(..., allow_placeholders: bool = False):
    # Validate metadata fields
    is_valid, unresolved = _validate_fields(
        metadata or {},
        allow_placeholders=allow_placeholders
    )
    if not is_valid:
        return {
            "action": "rejected-unresolved-tokens",
            "unresolved_tokens": unresolved,
            "reason": "Metadata contains unresolved template tokens"
        }
    # ... proceed with logging ...
```

#### Runtime parity behavior (implemented)

`log_cycle()` now enforces unresolved-token validation on the **metadata path** before dispatching to `scripts/log_prompt.py`.

- Mode resolution follows the same precedence pattern as append commands:
    1. `ORCHESTRATOR_PLACEHOLDER_MODE` when set to `strict`, `warn`, or `permissive`
    2. otherwise `allow_placeholders=True` maps to `warn`
    3. default is `strict`
- In `strict` mode, unresolved tokens in metadata cause an early structured rejection with `action: rejected-unresolved-tokens`, `reason: Metadata contains unresolved template tokens`, and included `placeholder_mode` + `unresolved_tokens` fields.
- In `warn` mode, unresolved metadata tokens are logged as warnings and persistence continues.
- In `permissive` mode, unresolved metadata tokens are allowed (with warning output).
- When `allow_placeholders=True`, `log_cycle()` also forwards `--allow-placeholders` to `scripts/log_prompt.py` so hook-layer and append-layer behavior stay aligned.

### 3. Template Rendering

When rendering structured evidence or cycle metadata, auto-populate known tokens:

```python
def render_template(template_str: str, context: Dict[str, Any]) -> str:
    """Render template with context, then check for remaining unresolved tokens."""
    # Render all known tokens
    rendered = template_str.format_map({
        'CYCLE_ID': context.get('cycle_id', ''),
        'TIMESTAMP': context.get('timestamp', ''),
        'TIMESTAMP_ISO': context.get('timestamp_iso', ''),
    })
    
    # Check for unresolved tokens after rendering
    is_valid, unresolved = check_unresolved_tokens(rendered)
    if not is_valid:
        raise ValueError(f"Template rendering left unresolved tokens: {unresolved}")
    
    return rendered
```

## Override Mechanism

For legitimate cases where placeholders are intentional or will be resolved later:

```bash
# Override validation (logs warning)
python scripts/log_prompt.py /full-log --allow-placeholders "message with {{PLACEHOLDER}}"
```

When `--allow-placeholders` is used:

1. Validation still runs and identifies tokens
2. Tokens are logged to `stderr` as a warning
3. Content is appended despite tokens
4. Warning is also recorded in log metadata for audit trail

## Configuration

### Environment Variables

- `ORCHESTRATOR_PLACEHOLDER_MODE`:
  - `"strict"` (default): Reject unresolved tokens
  - `"warn"`: Log warnings but append anyway
  - `"permissive"`: Silently append (not recommended)

### Default Command-Line Behavior

- `log_prompt.py` uses `strict` mode by default
- `--allow-placeholders` flag switches to `warn` mode
- `ORCHESTRATOR_PLACEHOLDER_MODE` env var overrides both

## Testing

Tests MUST validate:

1. ✓ Valid content without tokens is accepted
2. ✓ Unresolved `{{CYCLE_ID}}` tokens are rejected (strict)
3. ✓ Unresolved `${TIMESTAMP}` tokens are rejected (strict)
4. ✓ Unresolved `[PLACEHOLDER]` tokens are rejected (strict)
5. ✓ Unresolved `{{TODO}}` tokens are rejected (strict)
6. ✓ Multiple unresolved tokens are reported together
7. ✓ `--allow-placeholders` flag warns but accepts (warn mode)
8. ✓ Resolved tokens (`"cycle-123"` instead of `{{CYCLE_ID}}`) are accepted
9. ✓ Partial token matches (e.g., `{{not_a_token}}` without underscores) are accepted (no false positives)
10. ✓ Environment variable override works (`ORCHESTRATOR_PLACEHOLDER_MODE=permissive`)

See `hooks/test_placeholder_validation.py` for comprehensive test coverage.

## Examples

### ✓ Valid Content

```json
{
  "cycle_id": "CYC-20260613-150000-ABCD",
  "timestamp": "2026-06-13T15:00:00Z",
  "observation": "Logging system behavior",
  "action_taken": "Validated log schema"
}
```

### ✗ Invalid Content (Rejected in Strict Mode)

```json
{
  "cycle_id": "{{CYCLE_ID}}",  # ERROR: Unresolved token
  "timestamp": "${TIMESTAMP}",  # ERROR: Unresolved token
  "note": "[TODO: update this later]"  # ERROR: Unresolved token
}
```

## Backwards Compatibility

- Existing logs that were appended before this policy was implemented are not retroactively validated
- New appends going forward will be validated
- Legacy scripts using `log_prompt.py` without templates will see no change
- Scripts using templates must either:
  - Pre-render tokens before calling `log_prompt.py`, OR
  - Use `--allow-placeholders` flag and update calling code

## Related Policies

- `Trust.Boundary.md` — Script execution trust boundaries
- `Logging.Policy.md` — Logging level semantics
- `OPERATIONAL_TRUTH.md` — Operational workflows and prompt commands
