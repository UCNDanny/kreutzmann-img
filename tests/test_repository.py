import importlib.util
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dependencies', ROOT / 'scripts/dependencies.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RepositoryTests(unittest.TestCase):
    def test_build_inputs_are_pinned(self):
        lock = json.loads((ROOT / 'dependencies.lock.json').read_text())
        for image in lock['bases'].values():
            self.assertRegex(image, r'@sha256:[a-f0-9]{64}$')
        self.assertRegex(lock['go_fips_module'], r'^v\d+\.\d+\.\d+$')
        for name in ('oauth2-proxy', 'keycloak'):
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
    def test_no_broad_health_bypass(self):
        compose = (ROOT / 'docker-compose.yml').read_text()
        self.assertNotIn('SKIP_AUTH_ROUTES', compose)
        self.assertNotIn('sslmode=require', compose)
        self.assertNotIn('9000:9000', compose)

if __name__ == '__main__':
    unittest.main()
