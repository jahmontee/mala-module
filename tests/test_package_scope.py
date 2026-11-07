# SPDX-License-Identifier: MIT
"""Keep this repository's release builder exclusive to Mala."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from package_v2 import PREFIXES, package, usb_source_files


class PackageScopeTests(unittest.TestCase):
    def test_documentation_images_omitted_and_runtime_graphics_and_source_preserved(self):
        required = {
            'ui/qml/mala/assets/knob-body.png': b'knob artwork',
            'ui/qml/mala/assets/silver-panel.png': b'panel artwork',
            'ui/qml/mala/assets/silver-button.png': b'button artwork',
            'src/dsp/mala.cpp': b'processor source',
            'installer/transaction.py': b'installer source',
            'LICENSE': b'license notice',
            'docs/USB-INSTALL.md': b'instructions',
            'docs/images/README.md': b'non-image documentation',
        }
        source = dict(required, **{'docs/images/mala-v2.png': b'screenshot',
                                   'docs/images/example.JPG': b'optional illustration'})
        self.assertEqual(usb_source_files(source), required)

    def test_only_mala_can_be_packaged(self):
        self.assertEqual(PREFIXES, {'mala': 'mala-hector'})
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'unexpected'
            with self.assertRaisesRegex(ValueError, 'Mala only'):
                package('unrelated-product', output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
