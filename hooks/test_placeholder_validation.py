"""Tests for placeholder validation policy."""

import os
import sys
import unittest
from pathlib import Path

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestrator_runtime import check_unresolved_tokens


class TestPlaceholderValidation(unittest.TestCase):
    """Test placeholder/unresolved token detection."""

    def setUp(self):
        """Set up test fixtures."""
        if "ORCHESTRATOR_PLACEHOLDER_MODE" in os.environ:
            del os.environ["ORCHESTRATOR_PLACEHOLDER_MODE"]

    def tearDown(self):
        """Clean up after tests."""
        if "ORCHESTRATOR_PLACEHOLDER_MODE" in os.environ:
            del os.environ["ORCHESTRATOR_PLACEHOLDER_MODE"]

    def test_valid_content_without_tokens(self) -> None:
        """Valid content without any tokens should be accepted."""
        content = "This is a normal log entry with no special tokens."
        is_valid, tokens = check_unresolved_tokens(content)
        self.assertTrue(is_valid, "Expected valid content")
        self.assertEqual(len(tokens), 0, "Expected no tokens found")

    def test_unresolved_cycle_id_token_rejected(self) -> None:
        """Unresolved {{CYCLE_ID}} token should be detected and rejected."""
        content = 'Cycle ID: {{CYCLE_ID}}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for {{CYCLE_ID}}")
        self.assertIn("{{CYCLE_ID}}", tokens)

    def test_unresolved_timestamp_token_rejected(self) -> None:
        """Unresolved {{TIMESTAMP}} token should be detected and rejected."""
        content = 'Timestamp: {{TIMESTAMP}}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for {{TIMESTAMP}}")
        self.assertIn("{{TIMESTAMP}}", tokens)

    def test_unresolved_shell_var_token_rejected(self) -> None:
        """Unresolved ${VAR} shell variable token should be detected."""
        content = 'Path: ${MY_PATH}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for ${MY_PATH}")
        self.assertIn("${MY_PATH}", tokens)

    def test_unresolved_bracket_placeholder_rejected(self) -> None:
        """Unresolved [PLACEHOLDER] token should be detected and rejected."""
        content = 'Note: [PLACEHOLDER]'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for [PLACEHOLDER]")
        self.assertIn("[PLACEHOLDER]", tokens)

    def test_unresolved_todo_token_rejected(self) -> None:
        """Unresolved {{TODO}} token should be detected and rejected."""
        content = 'Action: {{TODO: implement this}}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for {{TODO}}")
        self.assertGreater(len(tokens), 0, "Expected at least one token")

    def test_unresolved_fixme_token_rejected(self) -> None:
        """Unresolved [FIXME] token should be detected and rejected."""
        content = 'Bug: [FIXME: memory leak]'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure for [FIXME]")
        self.assertGreater(len(tokens), 0, "Expected at least one token")

    def test_multiple_unresolved_tokens_reported(self) -> None:
        """Multiple unresolved tokens should all be reported."""
        content = 'Cycle: {{CYCLE_ID}}, Timestamp: {{TIMESTAMP}}, Path: ${MY_PATH}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected validation failure")
        # Note: Some patterns may match multiple times, so we just check that all tokens are reported
        # {{CYCLE_ID}} might match both CYCLE_ID pattern and generic _ID pattern
        self.assertGreaterEqual(len(tokens), 3, f"Expected at least 3 tokens, got {len(tokens)}: {tokens}")
        self.assertIn('{{CYCLE_ID}}', tokens)
        self.assertIn('{{TIMESTAMP}}', tokens)
        self.assertIn('${MY_PATH}', tokens)

    def test_allow_placeholders_flag_warns_but_accepts(self) -> None:
        """When allow_placeholders=True, content with tokens should be warned but accepted."""
        content = 'Cycle: {{CYCLE_ID}}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=True)
        self.assertTrue(is_valid, "Expected acceptance with allow_placeholders=True")
        self.assertGreater(len(tokens), 0, "Expected tokens to be identified")

    def test_resolved_token_accepted(self) -> None:
        """Resolved tokens (actual values) should be accepted."""
        content = 'Cycle: CYC-20260613-150000-ABCD'
        is_valid, tokens = check_unresolved_tokens(content)
        self.assertTrue(is_valid, "Expected resolved value to be accepted")
        self.assertEqual(len(tokens), 0, "Expected no tokens found")

    def test_false_positive_avoidance(self) -> None:
        """Content with similar patterns but not exact tokens should not trigger false positives."""
        content = 'Variable {my_var} is not a template token'
        is_valid, tokens = check_unresolved_tokens(content)
        # {my_var} without underscore prefix shouldn't match our strict patterns
        # This test verifies we don't over-match
        # If this fails, we're being too broad in pattern matching
        self.assertTrue(is_valid or len(tokens) == 0, "Expected false positive avoidance")

    def test_case_insensitive_matching(self) -> None:
        """Token matching should be case-insensitive where appropriate."""
        content = '{{cycle_id}}'  # lowercase
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        # Pattern is CYCLE_ID but content is cycle_id - case insensitive search
        self.assertFalse(is_valid, "Expected case-insensitive matching")

    def test_mixed_valid_and_invalid_content(self) -> None:
        """Mixed content with some valid and some invalid tokens should reject the whole."""
        content = 'Started at {{TIMESTAMP}}, this is normal text, ended successfully'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected failure for mixed content with unresolved token")
        self.assertIn("{{TIMESTAMP}}", tokens)

    def test_empty_content(self) -> None:
        """Empty content should be valid."""
        is_valid, tokens = check_unresolved_tokens("")
        self.assertTrue(is_valid, "Expected empty content to be valid")
        self.assertEqual(len(tokens), 0, "Expected no tokens in empty content")

    def test_whitespace_only_content(self) -> None:
        """Whitespace-only content should be valid."""
        is_valid, tokens = check_unresolved_tokens("   \n  \t  ")
        self.assertTrue(is_valid, "Expected whitespace-only content to be valid")
        self.assertEqual(len(tokens), 0, "Expected no tokens in whitespace content")

    def test_id_pattern_matching(self) -> None:
        """{{*_ID}} patterns should be detected."""
        content = 'Request ID: {{REQUEST_ID}}'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected {{REQUEST_ID}} to be detected")

    def test_bracket_fill_me_in(self) -> None:
        """[FILL_ME_IN] pattern should be detected."""
        content = 'Value: [FILL_ME_IN]'
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected [FILL_ME_IN] to be detected")

    def test_json_with_unresolved_tokens(self) -> None:
        """JSON content with unresolved tokens should be rejected."""
        json_content = '''{
            "cycle_id": "{{CYCLE_ID}}",
            "status": "success"
        }'''
        is_valid, tokens = check_unresolved_tokens(json_content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected JSON with {{CYCLE_ID}} to be rejected")

    def test_multiline_content_with_tokens(self) -> None:
        """Multiline content with unresolved tokens should be detected."""
        content = '''Observation log:
- Cycle: {{CYCLE_ID}}
- Status: success
- Notes: normal operation'''
        is_valid, tokens = check_unresolved_tokens(content, allow_placeholders=False)
        self.assertFalse(is_valid, "Expected multiline content to be checked")
        self.assertIn("{{CYCLE_ID}}", tokens)


if __name__ == "__main__":
    unittest.main()
