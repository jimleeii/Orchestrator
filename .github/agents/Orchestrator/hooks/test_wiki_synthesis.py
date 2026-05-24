from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))


def _load_module(module_name: str, relative_path: Path):
    module_path = ORCHESTRATOR_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load module from {module_path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


analyze_logs = _load_module('orchestrator_analyze_logs_test', Path('scripts') / 'analyze_logs.py')
synthesize_wiki = _load_module('orchestrator_synthesize_wiki_test', Path('scripts') / 'synthesize_wiki.py')
search_wiki = _load_module('orchestrator_search_wiki_test', Path('scripts') / 'search_wiki.py')


BEHAVIOR_LOG = """# Behavior-Log.md

### OBS-20260524-101500

- Timestamp (UTC): 2026-05-24T10:15:00+00:00
- Project Request: Stabilize prompt mappings
- Model Selection: selected_model=gpt-5.4-mini | task_type=implementation | criticality=P1
- Contract Score: 92
- Outcome: pass
- Follow-up Action: Keep the explicit registry approach
- Failure Mode (if any):
- Root Cause Hypothesis: hard-coded mapping drift
- Related: [Behavior-Patterns](Behavior-Patterns.md#PAT-20260524-101500)
Cycle: CYC-20260524-101500-ABCD

### OBS-20260524-111500

- Timestamp (UTC): 2026-05-24T11:15:00+00:00
- Project Request: Improve routing quality
- Model Selection: selected_model=gpt-5.4 | task_type=analysis | criticality=P1
- Contract Score: 74
- Outcome: revise
- Failure Mode (if any): routing mismatch
- Root Cause Hypothesis: missing prompt registry validation
- Follow-up Action: tighten validator and knowledge synthesis
Cycle: CYC-20260524-111500-BCDE
"""

SKILL_LOG = """# Skill-Usage-Log.md

### SKL-20260524101500

- Timestamp (UTC): 2026-05-24T10:15:00+00:00
- Routing Path: single-agent
- Skills Used (ordered): prompt-optimizer, test-driven-development
- Invocation Reason: Stabilize prompt mappings
Cycle: CYC-20260524-101500-ABCD

### SKL-20260524111500

- Timestamp (UTC): 2026-05-24T11:15:00+00:00
- Routing Path: multi-agent
- Skills Used (ordered): prompt-optimizer, systematic-debugging
- Invocation Reason: Improve routing quality
Cycle: CYC-20260524-111500-BCDE
"""

PATTERNS_LOG = """# Behavior-Patterns.md

### PAT-20260524-101500

- Signal: prompt mapping drift
- Impact: high
- Status: candidate

### PAT-20260524-111500

- Signal: routing mismatch
- Impact: medium
- Status: applied
"""

BACKLOG_LOG = """# Learning-Backlog.md

### LRN-20260524-101500

- Priority: high
- Problem: prompt mapping drift
- Proposed Change: validate prompt mappings in CI
- Scope: routing
- Status: pending
- Linked Pattern: [Behavior-Patterns](Behavior-Patterns.md#PAT-20260524-101500)
- Date: 2026-05-24
"""

RUNBOOK_LOG = """# Runbook.md

### CHG-20260524-101500

- Date: 2026-05-24
- Change Applied: Introduced shared prompt registry
- Observed Result: Fewer mismatches during validation
- Decision: keep
"""

PROJECT_CONTEXT = """# Project-Context-Log.md

### CTX-20260524-101500

- Timestamp (UTC): 2026-05-24T10:15:00+00:00
- Project/Request: Stabilize prompt mappings
- Stage: checkpoint
"""

HOME = "# Home\n"


class WikiSynthesisTests(unittest.TestCase):
    def _build_wiki(self, root: Path) -> Path:
        wiki = root / '.wiki' / 'orchestrator'
        wiki.mkdir(parents=True, exist_ok=True)
        (wiki / 'Behavior-Log.md').write_text(BEHAVIOR_LOG, encoding='utf-8')
        (wiki / 'Skill-Usage-Log.md').write_text(SKILL_LOG, encoding='utf-8')
        (wiki / 'Behavior-Patterns.md').write_text(PATTERNS_LOG, encoding='utf-8')
        (wiki / 'Learning-Backlog.md').write_text(BACKLOG_LOG, encoding='utf-8')
        (wiki / 'Runbook.md').write_text(RUNBOOK_LOG, encoding='utf-8')
        (wiki / 'Project-Context-Log.md').write_text(PROJECT_CONTEXT, encoding='utf-8')
        (wiki / 'Home.md').write_text(HOME, encoding='utf-8')
        return wiki

    def test_collect_metrics_emits_richer_phase_two_and_three_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wiki = self._build_wiki(Path(temp_dir))
            metrics = analyze_logs.collect_metrics(wiki, cycles=10, stale_days=30)

        self.assertEqual(metrics['cycle_count'], 2)
        self.assertIn('model_quality', metrics)
        self.assertIn('routing_quality', metrics)
        self.assertIn('contract_feedback', metrics)
        self.assertEqual({item['model'] for item in metrics['model_quality']}, {'gpt-5.4', 'gpt-5.4-mini'})

    def test_synthesize_wiki_generates_index_glossary_and_learned_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wiki = self._build_wiki(Path(temp_dir))
            pages = synthesize_wiki.generate_knowledge_pages(wiki, cycles=10, stale_days=30)

            index_text = pages[wiki / 'knowledge' / 'Index.md']
            model_text = pages[wiki / 'knowledge' / 'Learned-Model-Selection.md']
            glossary_text = pages[wiki / 'knowledge' / 'Glossary.md']

        self.assertIn('Top Pattern Signals', index_text)
        self.assertIn('gpt-5.4-mini', model_text)
        self.assertIn('Contract score', glossary_text)

    def test_search_wiki_returns_relevant_knowledge_and_log_hits(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wiki = self._build_wiki(Path(temp_dir))
            synthesize_wiki.generate_knowledge_pages(wiki, cycles=10, stale_days=30)
            results = search_wiki.search_wiki_pages(wiki, 'routing quality', limit=5)

        self.assertTrue(results)
        self.assertIn('routing', results[0].title.lower())


if __name__ == '__main__':
    unittest.main()
