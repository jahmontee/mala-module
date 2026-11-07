# SPDX-License-Identifier: MIT
"""Keep this repository's release builder exclusive to Mala."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package_v2 import PREFIXES, package


class PackageScopeTests(unittest.TestCase):
    def test_only_mala_can_be_packaged(self):
        self.assertEqual(PREFIXES, {'mala': 'mala-hector'})
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'unexpected'
            with self.assertRaisesRegex(ValueError, 'Mala only'):
                package('unrelated-product', output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
