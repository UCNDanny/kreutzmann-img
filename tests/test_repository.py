import importlib.util
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dependencies', ROOT / 'scripts/dependencies.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RepositoryTests(unittest.TestCase):
    def test_go_security_updates_never_downgrade_to_avoid_an_advisory(self):
        with patch.object(module, 'fetch', return_value=b'v1.1.0\nv1.2.0\nv1.3.0'), \
             patch.object(module, 'osv_affected', side_effect=lambda name, version: version != 'v1.1.0'):
            with self.assertRaisesRegex(ValueError, 'at or above v1.2.0'):
                module.latest_go_module('example.org/module', 'v1.2.0')

    def test_go_security_updates_choose_the_newest_unaffected_stable_version(self):
        with patch.object(module, 'fetch', return_value=b'v1.1.0\nv1.2.0\nv1.3.0\nv2.0.0-rc.1'), \
             patch.object(module, 'osv_affected', side_effect=lambda name, version: version == 'v1.3.0'):
            self.assertEqual(module.latest_go_module('example.org/module', 'v1.1.0'), 'v1.2.0')

    def test_base_defaults_match_the_lock(self):
        lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
        for image in module.IMAGES:
            source = (ROOT / ('Dockerfile.' + image)).read_text()
            for name, ref in lock['bases'].items():
                match = re.search(r'^ARG ' + name.upper() + r'_IMAGE=(.+)$', source, re.M)
                if match:
                    self.assertEqual(match.group(1), ref)

    def test_build_inputs_are_pinned(self):
        lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
        for image in lock['bases'].values():
            self.assertRegex(image, r'@sha256:[a-f0-9]{64}$')
        self.assertRegex(lock['go_fips_module'], r'^v\d+\.\d+\.\d+$')
        for name in module.IMAGES:
            args = module.build_args(name)
            dockerfile = (ROOT / ('Dockerfile.' + name)).read_text()
            declared = set(re.findall(r'^ARG (\w+)', dockerfile, re.M))
            self.assertFalse(set(args) - declared)
            self.assertFalse(declared - set(args) - {'TARGETOS', 'TARGETARCH'})
            for key, value in args.items():
                if key.endswith('SHA256'):
                    self.assertRegex(value, r'^[a-f0-9]{64}$')
    def test_actions_are_commit_pinned(self):
        for path in (ROOT / '.github/workflows').glob('*.yml'):
            for ref in re.findall(r'uses:\s*(\S+)', path.read_text()):
                self.assertRegex(ref, r'^[\w-]+/[\w-]+@[a-f0-9]{40}$')
    def test_keycloak_security_update_replacements_are_jars(self):
        lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
        for update in lock['keycloak_security_updates']:
            self.assertTrue(update['file'].endswith('.jar'))
            if replacement := update.get('replacement_file'):
                self.assertTrue(replacement.endswith('.jar'))
                self.assertNotEqual(replacement, update['file'])
    def test_no_broad_health_bypass(self):
        compose = (ROOT / 'docker-compose.yml').read_text()
        self.assertNotIn('SKIP_AUTH_ROUTES', compose)
        self.assertNotIn('sslmode=require', compose)
        self.assertNotIn('9000:9000', compose)

if __name__ == '__main__':
    unittest.main()
