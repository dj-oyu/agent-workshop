import hashlib
from pathlib import Path
import tempfile
import unittest
from install_skill import install

class InstallSkillTest(unittest.TestCase):
    def package(self, root):
        source = root / 'source'
        source.mkdir()
        (source / 'SKILL.md').write_text('synthetic skill')
        digest = hashlib.sha256((source / 'SKILL.md').read_bytes()).hexdigest()
        (source / 'SHA256SUMS').write_text(digest + '  SKILL.md\n')
        (source / 'private-case.json').write_text('must not copy')
        return source

    def test_only_manifest_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = self.package(root)
            destination = root / 'skills' / 'problem-loop-harness'
            install(source, destination)
            self.assertEqual((destination / 'SKILL.md').read_text(), 'synthetic skill')
            self.assertFalse((destination / 'private-case.json').exists())
            with self.assertRaises(ValueError): install(source, destination)

    def test_bad_hash_has_no_install(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = self.package(root)
            (source / 'SKILL.md').write_text('changed')
            destination = root / 'problem-loop-harness'
            with self.assertRaises(ValueError): install(source, destination)
            self.assertFalse(destination.exists())

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = self.package(root)
            original = source / 'SKILL.md'
            original.rename(root / 'outside')
            original.symlink_to(root / 'outside')
            with self.assertRaises(ValueError): install(source, root / 'problem-loop-harness')
