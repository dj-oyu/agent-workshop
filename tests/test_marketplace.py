"""Integration check using the installed Codex parser, not a schema imitation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('codex'), 'Codex CLI required')
class MarketplaceInstall(unittest.TestCase):
    def test_real_marketplace_and_plugin_install(self):
        with tempfile.TemporaryDirectory(prefix='agent-workshop-check-') as tmp:
            env = dict(os.environ, CODEX_HOME=tmp)
            def cli(*args):
                return json.loads(subprocess.check_output(['codex', 'plugin', *args, '--json'], env=env, text=True))
            added = cli('marketplace', 'add', str(ROOT))
            self.assertEqual(added['marketplaceName'], 'agent-workshop')
            installed = cli('add', 'agent-workshop@agent-workshop')
            cache = Path(installed['installedPath'])
            skill = cache / 'skills/problem-loop-harness'
            original = ROOT / '.agents/skills/problem-loop-harness'
            for entry in (original / 'SHA256SUMS').read_text().splitlines():
                digest, name = entry.split(maxsplit=1)
                self.assertEqual(hashlib.sha256((skill / name).read_bytes()).hexdigest(), digest)
            self.assertEqual((skill / 'SKILL.md').read_bytes(), (original / 'SKILL.md').read_bytes())
            entries = cli('list')['installed']
            self.assertTrue(any(p['pluginId'] == 'agent-workshop@agent-workshop' and p['enabled'] for p in entries))
            subprocess.run(['python3', '-m', 'unittest', '-q'], cwd=skill, env=env, check=True)

if __name__ == '__main__':
    unittest.main()
