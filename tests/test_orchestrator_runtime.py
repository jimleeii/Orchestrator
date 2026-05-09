import os
import json
import unittest
import tempfile
from contextlib import contextmanager

from src import orchestrator_runtime as rt


@contextmanager
def chdir(path):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class TestOrchestratorRuntime(unittest.TestCase):

    def test_init_orchestrator_writes_manifest(self):
        manifest_path = os.path.join(os.path.dirname(__file__), 'tmp_skills_manifest.json')
        if os.path.exists(manifest_path):
            os.remove(manifest_path)
        try:
            m = rt.init_orchestrator(skills_dir='skills', manifest_path=manifest_path)
            self.assertIsInstance(m, dict)
            self.assertTrue(os.path.exists(manifest_path))
            with open(manifest_path, encoding='utf8') as handle:
                loaded = json.loads(handle.read())
            self.assertEqual(m, loaded)
        finally:
            if os.path.exists(manifest_path):
                os.remove(manifest_path)

    def test_run_script_executes_python(self):
        # create a small python script
        tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp_scripts')
        os.makedirs(tmp_dir, exist_ok=True)
        script = os.path.join(tmp_dir, 'echo.py')
        with open(script, 'w', encoding='utf8') as f:
            f.write('print("ORCH_TEST_HELLO")\n')
        try:
            out = rt.run_script(script)
            self.assertIn('ORCH_TEST_HELLO', out)
        finally:
            try:
                os.remove(script)
                os.rmdir(tmp_dir)
            except Exception:
                pass

    def test_handle_request_runs_skill_script(self):
        # create a temporary skill folder with a python script
        skills_base = os.path.join(os.path.dirname(__file__), '..', 'skills')
        skills_base = os.path.abspath(skills_base)
        tmp_skill = os.path.join(skills_base, 'tmp_skill')
        os.makedirs(tmp_skill, exist_ok=True)
        script = os.path.join(tmp_skill, 'run_me.py')
        try:
            with open(script, 'w', encoding='utf8') as f:
                f.write('print("SKILL_SCRIPT_RAN")\n')

            # run handler
            out = rt.handle_request('test', user='u', run_skill='tmp_skill')
            self.assertIn('SKILL_SCRIPT_RAN', (out.get('skill_output') or ''))
        finally:
            try:
                if os.path.exists(script):
                    os.remove(script)
                if os.path.isdir(tmp_skill):
                    os.rmdir(tmp_skill)
            except Exception:
                pass

    def test_prepare_dispatch_payload(self):
        payload = rt.prepare_dispatch_payload('prepare-prompt', user='u')
        self.assertIn('prompt', payload)
        self.assertIn('parent_context', payload)
        self.assertIn('persistence', payload['parent_context'])

    def test_handle_request_logs_skills_from_prompt_and_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            skills_dir = os.path.join(temp_dir, 'skills', 'tmp_skill')
            os.makedirs(skills_dir, exist_ok=True)
            script = os.path.join(skills_dir, 'emit.py')
            with open(script, 'w', encoding='utf8') as handle:
                handle.write('print("output mentions contract-validator")\n')

            with chdir(temp_dir):
                result = rt.handle_request(
                    'Please use prompt-optimizer before you answer.',
                    user='u',
                    run_skill='tmp_skill',
                    skill_script_name='emit.py',
                )

                self.assertIn('skill_usage', result)
                self.assertEqual(result['skill_usage']['skills'], ['prompt-optimizer', 'contract-validator'])

                log_path = os.path.join(temp_dir, '.wiki', 'orchestrator', 'Skill-Usage-Log.md')
                self.assertTrue(os.path.exists(log_path))
                with open(log_path, encoding='utf8') as handle:
                    log_text = handle.read()
                self.assertIn('prompt-optimizer', log_text)
                self.assertIn('contract-validator', log_text)


if __name__ == '__main__':
    unittest.main()
