# Follow-plan execution mode — system prompt snippets

When dispatching work with `metadata.execution_mode = "follow_plan"`, include a short system or assistant instruction to the subagent like the following:

- "You are in follow-plan mode. Do NOT provide inline suggestions that deviate from the plan. If you have a suggestion, write it as a 'SUGGESTION:' block and include a short title. Continue executing the plan unless explicitly asked to pause."
- "You are in follow-plan mode. Do NOT provide inline suggestions that deviate from the plan. If you have a suggestion, write it as a 'SUGGESTION:' block and include a short title. Prefer a structured JSON suggestion: `SUGGESTION: {\"title\": \"Short title\", \"body\": \"Longer text\", \"tags\": [\"idea\"], \"severity\": \"low\"}`. Continue executing the plan unless explicitly asked to pause."

- "For progress updates, emit structured checklist updates in the form `CHECKLIST_UPDATE: {\"step_id\": \"S1\", \"status\": \"done\"}` (JSON string). Free-text checklist updates may be ignored."

- "If you detect a blocker that requires human intervention, emit `CHECKLIST_UPDATE: {\"step_id\": \"S2\", \"status\": \"blocked\", \"reason\": \"...\"}` and stop; do not continue further steps."

These snippets are recommendations — to enforce follow-plan behavior, the Orchestrator persists only structured checklist updates and logs suggestions to `.suggestions/suggestions.jsonl` for later evaluation.
