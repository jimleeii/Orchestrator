import unittest

from src.model_resolver import resolve_model_for_subagent


class TestModelResolver(unittest.TestCase):

    def setUp(self):
        # simple catalog with tiers
        self.catalog = {
            "gpt-5-mini": {"tier": "balanced"},
            "gpt-5.3-codex": {"tier": "frontier"},
            "gpt-5.4-mini": {"tier": "balanced", "name": "GPT-5.4 mini"},
            "claude-sonnet": {"tier": "frontier"},
            "economy-1": {"tier": "economy"},
        }
        self.global_default = "gpt-5-mini"

    def test_spawn_model_honored(self):
        payload = {"model": "gpt-5.3-codex"}
        parent = {"selected_model": "claude-sonnet"}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.3-codex")
        self.assertEqual(r["source"], "subagent_assigned_model")

    def test_spawn_model_display_name_alias_is_normalized(self):
        payload = {"model": "GPT-5.4 mini"}
        parent = {}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.4-mini")
        self.assertEqual(r["source"], "subagent_assigned_model")

    def test_preferred_model_display_name_alias_is_normalized(self):
        payload = {"preferred_model": "GPT-5.4 mini"}
        parent = {}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.4-mini")
        self.assertEqual(r["source"], "preferred_model")

    def test_spawn_model_blocked_falls_to_parent(self):
        payload = {"model": "economy-1"}
        parent = {"selected_model": "gpt-5.3-codex"}
        # enforce minimum tier balanced -> economy should be blocked
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default, minimum_tier="balanced")
        self.assertEqual(r["model"], "gpt-5.3-codex")
        self.assertEqual(r["source"], "parent_selected_model")
        self.assertTrue(r["fallback_used"])
        self.assertIn("requested model 'economy-1'", r["fallback_reason"])

    def test_unknown_spawn_model_falls_to_parent(self):
        payload = {"model": "NotARealModelName"}
        parent = {"selected_model": "gpt-5.3-codex"}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.3-codex")
        self.assertEqual(r["source"], "parent_selected_model")
        self.assertTrue(r["fallback_used"])
        self.assertIn("requested model", r["fallback_reason"])

    def test_precedence_spawn_over_preferred_parent_cycle_global(self):
        payload = {
            "model": "gpt-5.3-codex",
            "preferred_model": "gpt-5-mini",
        }
        parent = {
            "selected_model": "claude-sonnet",
            "cycle_selected_model": "gpt-5-mini",
        }
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.3-codex")
        self.assertEqual(r["source"], "subagent_assigned_model")

    def test_no_spawn_inherits_parent(self):
        payload = {}
        parent = {"selected_model": "claude-sonnet"}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "claude-sonnet")
        self.assertEqual(r["source"], "parent_selected_model")

    def test_cycle_then_global(self):
        payload = {}
        parent = {"cycle_selected_model": "gpt-5.3-codex"}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], "gpt-5.3-codex")
        self.assertEqual(r["source"], "cycle_selected_model")

    def test_global_fallback(self):
        payload = {}
        parent = {}
        r = resolve_model_for_subagent(payload, parent, self.catalog, self.global_default)
        self.assertEqual(r["model"], self.global_default)
        self.assertEqual(r["source"], "global_default_model")

    def test_none_available(self):
        # enforce P0 so only frontier allowed, but no frontier present in catalog
        catalog = {"economy-1": {"tier": "economy"}}
        payload = {"model": "economy-1"}
        parent = {}
        r = resolve_model_for_subagent(payload, parent, catalog, "economy-1", minimum_tier="frontier")
        self.assertIsNone(r["model"])
        self.assertEqual(r["source"], "none_available")


if __name__ == "__main__":
    unittest.main()
