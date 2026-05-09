import os
import json
import unittest

from src.skill_loader import discover_skills, save_manifest


class TestSkillLoader(unittest.TestCase):

    def test_discover_skills_non_empty(self):
        skills = discover_skills('skills')
        self.assertIsInstance(skills, dict)
        self.assertTrue(len(skills) > 0, "Expected to discover at least one skill under 'skills/'")
        for k, v in skills.items():
            self.assertIn('path', v)
            self.assertTrue(v['path'].endswith('SKILL.md'))
            self.assertIn('title', v)
            self.assertTrue(v['title'] is not None and v['title'] != '')
            self.assertIn('description', v)

    def test_save_and_load_manifest(self):
        skills = discover_skills('skills')
        tmp_manifest = os.path.join(os.path.dirname(__file__), 'tmp_manifest.json')
        try:
            save_manifest(skills, tmp_manifest)
            with open(tmp_manifest, encoding='utf8') as handle:
                loaded = json.loads(handle.read())
            self.assertEqual(skills, loaded)
        finally:
            if os.path.exists(tmp_manifest):
                os.remove(tmp_manifest)


if __name__ == '__main__':
    unittest.main()
