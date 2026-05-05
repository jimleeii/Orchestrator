# Markdown Policy

This file aligns Orchestrator-generated markdown with [Markdown.Rule.md](Markdown.Rule.md).

## Scope

Apply this checklist whenever Orchestrator creates or updates markdown files in this workspace, including wiki context logs.

Prompt intake policy is also in scope for markdown artifacts: when a user request is transformed into an execution-ready prompt, explicitly note that prompt normalization was performed via `prompt-optimizer` guidance.

## Alignment Checklist

1. Heading levels increment by one only.

  - Good: `#` -> `##` -> `###`
  - Avoid: `#` -> `###`

2. Use one heading style consistently.

  - Prefer ATX headings (`#`, `##`, `###`).
  - Do not mix setext (`===`, `---`) with ATX in the same file.

3. Use one unordered list marker consistently.

  - Prefer dash marker (`-`) across the file.

4. Keep list indentation consistent.

  - Same nesting level must align to the same column.

5. Use 2-space indentation for nested unordered lists.

6. Avoid trailing spaces.

  - No unnecessary spaces at line ends.

## Writing Profile for Orchestrator

Use this default profile when generating markdown:

- Heading style: ATX
- Unordered list marker: dash (`-`)
- Nested unordered list indentation: 2 spaces
- No trailing spaces

## Quick Self-Check Before Save

- Are heading levels sequential?
- Is heading style consistent?
- Are unordered lists using one marker?
- Is list indentation consistent and 2-space nested?
- Are trailing spaces removed?
- If this document records task intake or routing, does it state that prompt normalization happened before dispatch?

## Notes


If future rule settings in [Markdown.Rule.md](Markdown.Rule.md) change, update this alignment file and Orchestrator instructions together.

```yaml
pseudocode_markdown_alignment_check: |
  # Pseudocode: Validate markdown alignment rules for a file

  function check_markdown_file(path):
    text = read_file_text(path)
    findings = []

    # 1. Heading level sequence
    headings = extract_headings(text)
    if not headings_sequential(headings):
      findings.append({level: 'Medium', issue: 'Non-sequential heading levels', details: headings})

    # 2. Heading style consistency
    if not single_heading_style(headings):
      findings.append({level: 'Low', issue: 'Mixed heading styles'})

    # 3. Unordered list marker consistency
    list_markers = extract_list_markers(text)
    if not single_list_marker(list_markers):
      findings.append({level: 'Low', issue: 'Inconsistent unordered list markers', markers: list_markers})

    # 4. List indentation
    if not consistent_list_indentation(text, expected_indent=2):
      findings.append({level: 'Medium', issue: 'Inconsistent list indentation'})

    # 5. Trailing spaces
    if has_trailing_spaces(text):
      findings.append({level: 'Low', issue: 'Trailing spaces found'})

    # 6. Prompt normalization note for intake documents
    if is_intake_document(path) and not mentions_prompt_normalization(text):
      findings.append({level: 'Low', issue: 'Missing prompt normalization note for intake document'})

    return findings

  # Usage: run check_markdown_file during CI or before saving orchestrator-generated markdown.
```
