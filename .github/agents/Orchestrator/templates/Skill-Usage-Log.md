# Skill Usage Log

Track which skills were used per orchestration cycle and what should be reused later. Entries are populated from Copilot Chat input/output plus runtime invocation hints.

## Entry Template

### SKL-YYYYMMDDHHMMSS

- Timestamp (UTC):
- Request Type: chat-conversion
- Routing Path: direct | single-agent | multi-agent
- Subagent(s):
- Skills Used (ordered):
- Invocation Reason:
- Outcome Impact: positive | neutral | negative
- Reuse Note:

```yaml
entry_template: |
	### SKL-YYYYMMDDHHMMSS

	- Timestamp (UTC):
	- Request Type: chat-conversion
	- Routing Path: direct | single-agent | multi-agent
	- Subagent(s):
	- Skills Used (ordered):
	- Invocation Reason:
	- Outcome Impact: positive | neutral | negative
	- Reuse Note:
```

---
