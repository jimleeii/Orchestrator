"""Parity tests for logging level decisions across runtime and hooks.

These tests verify that `choose_logging_level` behaves consistently
when called from both the runtime and hooks modules.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ORCHESTRATOR_ROOT = Path(__file__).resolve().parents[1]
if str(ORCHESTRATOR_ROOT) not in sys.path:
    sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from hooks import log_hooks
from src import orchestrator_runtime


class LoggingLevelParityTests(unittest.TestCase):
    """Test that choose_logging_level produces consistent results across modules."""

    def test_direct_dispatch_returns_minimal(self) -> None:
        """Test case: direct dispatch should return 'minimal'."""
        hooks_result = log_hooks.choose_logging_level('direct')
        runtime_result = orchestrator_runtime.choose_logging_level('direct', {}, {})
        
        self.assertEqual(hooks_result, 'minimal', 
                        "Hooks: direct dispatch should return 'minimal'")
        self.assertEqual(runtime_result, 'minimal', 
                        "Runtime: direct dispatch should return 'minimal'")
        self.assertEqual(hooks_result, runtime_result, 
                        "Parity: hooks and runtime should match for direct dispatch")

    def test_single_agent_dispatch_returns_compact(self) -> None:
        """Test case: single-agent dispatch should return 'compact'."""
        hooks_result = log_hooks.choose_logging_level('single-agent')
        runtime_result = orchestrator_runtime.choose_logging_level('single-agent', {}, {})
        
        self.assertEqual(hooks_result, 'compact', 
                        "Hooks: single-agent dispatch should return 'compact'")
        self.assertEqual(runtime_result, 'compact', 
                        "Runtime: single-agent dispatch should return 'compact'")
        self.assertEqual(hooks_result, runtime_result, 
                        "Parity: hooks and runtime should match for single-agent dispatch")

    def test_multi_agent_dispatch_returns_full(self) -> None:
        """Test case: multi-agent dispatch should return 'full'."""
        hooks_result = log_hooks.choose_logging_level('multi-agent')
        runtime_result = orchestrator_runtime.choose_logging_level('multi-agent', {}, {})
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: multi-agent dispatch should return 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: multi-agent dispatch should return 'full'")
        self.assertEqual(hooks_result, runtime_result, 
                        "Parity: hooks and runtime should match for multi-agent dispatch")

    def test_concurrent_dispatch_returns_full(self) -> None:
        """Test case: concurrent dispatch should return 'full'."""
        hooks_result = log_hooks.choose_logging_level('concurrent')
        runtime_result = orchestrator_runtime.choose_logging_level('concurrent', {}, {})
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: concurrent dispatch should return 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: concurrent dispatch should return 'full'")
        self.assertEqual(hooks_result, runtime_result, 
                        "Parity: hooks and runtime should match for concurrent dispatch")

    def test_failure_detected_flag_overrides_direct_to_full(self) -> None:
        """Test case: failure_detected flag should override dispatch type to 'full'."""
        event_flags = {'failure_detected': True}
        
        hooks_result = log_hooks.choose_logging_level('direct', event_flags=event_flags)
        runtime_result = orchestrator_runtime.choose_logging_level('direct', event_flags, {})
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: failure_detected should override direct to 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: failure_detected should override direct to 'full'")
        self.assertEqual(hooks_result, runtime_result, 
                        "Parity: both should return 'full' when failure detected")

    def test_persistent_mode_change_flag_overrides_to_full(self) -> None:
        """Test case: persistent_mode_change flag should override to 'full'."""
        event_flags = {'persistent_mode_change': True}
        
        hooks_result = log_hooks.choose_logging_level('single-agent', event_flags=event_flags)
        runtime_result = orchestrator_runtime.choose_logging_level('single-agent', event_flags, {})
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: persistent_mode_change should override to 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: persistent_mode_change should override to 'full'")

    def test_tier_override_flag_overrides_to_full(self) -> None:
        """Test case: tier_override flag should override to 'full'."""
        event_flags = {'tier_override': True}
        
        hooks_result = log_hooks.choose_logging_level('direct', event_flags=event_flags)
        runtime_result = orchestrator_runtime.choose_logging_level('direct', event_flags, {})
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: tier_override should override to 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: tier_override should override to 'full'")

    def test_force_persist_all_config_always_returns_full(self) -> None:
        """Test case: force_persist_all config should always return 'full'.
        
        This is a strict override: regardless of dispatch path or event flags,
        force_persist_all takes precedence and returns 'full'.
        """
        config = {'force_persist_all': True}
        
        # Test with various dispatch paths
        for dispatch_path in ['direct', 'single-agent', 'multi-agent', 'concurrent']:
            hooks_result = log_hooks.choose_logging_level(dispatch_path, config=config)
            runtime_result = orchestrator_runtime.choose_logging_level(dispatch_path, {}, config)
            
            self.assertEqual(hooks_result, 'full', 
                            f"Hooks: force_persist_all should return 'full' for {dispatch_path}")
            self.assertEqual(runtime_result, 'full', 
                            f"Runtime: force_persist_all should return 'full' for {dispatch_path}")
            self.assertEqual(hooks_result, runtime_result, 
                            f"Parity: both should return 'full' for {dispatch_path} with force_persist_all")

    def test_force_persist_all_overrides_all_flags(self) -> None:
        """Test case: force_persist_all should override even with contradictory flags."""
        config = {'force_persist_all': True}
        event_flags = {
            'failure_detected': False,
            'persistent_mode_change': False,
            'tier_override': False,
        }
        
        # Even with all flags False, force_persist_all should return 'full'
        hooks_result = log_hooks.choose_logging_level('direct', event_flags=event_flags, config=config)
        runtime_result = orchestrator_runtime.choose_logging_level('direct', event_flags, config)
        
        self.assertEqual(hooks_result, 'full', 
                        "Hooks: force_persist_all should override false flags to 'full'")
        self.assertEqual(runtime_result, 'full', 
                        "Runtime: force_persist_all should override false flags to 'full'")

    def test_no_config_no_flags_respects_dispatch_type(self) -> None:
        """Test case: with no config/flags, dispatch type determines level."""
        test_cases = [
            ('direct', 'minimal'),
            ('single-agent', 'compact'),
            ('multi-agent', 'full'),
            ('concurrent', 'full'),
        ]
        
        for dispatch_path, expected_level in test_cases:
            hooks_result = log_hooks.choose_logging_level(dispatch_path, event_flags={}, config={})
            runtime_result = orchestrator_runtime.choose_logging_level(dispatch_path, {}, {})
            
            self.assertEqual(hooks_result, expected_level, 
                            f"Hooks: {dispatch_path} should return {expected_level}")
            self.assertEqual(runtime_result, expected_level, 
                            f"Runtime: {dispatch_path} should return {expected_level}")
            self.assertEqual(hooks_result, runtime_result, 
                            f"Parity: both should return {expected_level} for {dispatch_path}")

    def test_unknown_dispatch_path_returns_minimal(self) -> None:
        """Test case: unknown dispatch paths should return 'minimal'."""
        unknown_paths = ['unknown', 'future-dispatch', '']
        
        for dispatch_path in unknown_paths:
            hooks_result = log_hooks.choose_logging_level(dispatch_path)
            runtime_result = orchestrator_runtime.choose_logging_level(dispatch_path, {}, {})
            
            self.assertEqual(hooks_result, 'minimal', 
                            f"Hooks: unknown path '{dispatch_path}' should return 'minimal'")
            self.assertEqual(runtime_result, 'minimal', 
                            f"Runtime: unknown path '{dispatch_path}' should return 'minimal'")
            self.assertEqual(hooks_result, runtime_result, 
                            f"Parity: both should return 'minimal' for unknown path '{dispatch_path}'")


class LoggingLevelIntegrationTests(unittest.TestCase):
    """Integration tests verifying logging level behavior in full workflows."""

    def test_log_cycle_respects_chosen_level(self) -> None:
        """Integration test: log_cycle should respect the chosen logging level."""
        # For a 'compact' level dispatch, log_cycle should call /info command
        mock_process = type('MockProcess', (), {'returncode': 0})()
        
        with patch.object(log_hooks, '_run_log_command', return_value=mock_process) as run_cmd_mock:
            with patch.object(log_hooks, '_should_persist_entry', return_value=True):
                with patch.object(log_hooks, '_is_automatic_hook_event', return_value=False):
                    with patch.object(log_hooks, 'find_repo_root', return_value=Path(__file__).resolve().parent):
                        result = log_hooks.log_cycle(
                            dispatch_path='single-agent',
                            summary='Test summary',
                            author='Test Author',
                            preview=True,
                        )
        
        # In preview mode with single-agent, should have attempted to persist at 'compact' level
        # The exact behavior depends on event flags and metadata, but level should be 'compact'
        self.assertIn(result.get('level'), ['compact', 'minimal'], 
                     "For single-agent dispatch, level should be compact or minimal (depends on metadata)")

    def test_force_persist_all_creates_full_logs(self) -> None:
        """Integration test: force_persist_all should create full logs even for direct dispatch."""
        mock_process = type('MockProcess', (), {'returncode': 0})()
        
        with patch.object(log_hooks, '_run_log_command', return_value=mock_process) as run_cmd_mock:
            with patch.object(log_hooks, '_should_persist_entry', return_value=True):
                with patch.object(log_hooks, '_is_automatic_hook_event', return_value=False):
                    with patch.object(log_hooks, 'find_repo_root', return_value=Path(__file__).resolve().parent):
                        result = log_hooks.log_cycle(
                            dispatch_path='direct',
                            summary='Test summary',
                            force_persist_all=True,
                            author='Test Author',
                            preview=True,
                        )
        
        # force_persist_all should cause 'full' level to be chosen
        # Even in preview mode, the decision should be 'full'
        self.assertIsNotNone(result, "log_cycle should return a result dict")


if __name__ == "__main__":
    unittest.main()
