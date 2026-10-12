"""Preparation must preserve the input kit and reject incomplete/corrupt output."""
import hashlib
import tempfile
from pathlib import Path
import unittest
import prepare_kit


class PrepareKitTests(unittest.TestCase):
    def test_verified_copy_and_reject_existing_output(self):
        self.exercise(False)

    def test_corrupt_unchanged_file_rejects_output(self):
        self.exercise(True)

    def exercise(self, corrupt):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, remote, output = root/'base', root/'remote', root/'output'
            (source/'aot').mkdir(parents=True)
            (remote/'aot').mkdir(parents=True)
            (source/'aot/aot.json').write_text('old')
            (source/'kernel').write_text('corrupt' if corrupt else 'preserved')
            (remote/'aot/aot.json').write_text('new')
            kernel_hash = hashlib.sha256(b'preserved').hexdigest()
            (remote/'MANIFEST').write_text(
                prepare_kit.digest(remote/'aot/aot.json')+'  aot/aot.json\n'+kernel_hash+'  kernel\n')
            spec = {'url': remote.as_uri()+'/', 'revision': 'test',
                    'base_aot_sha256': prepare_kit.digest(source/'aot/aot.json'),
                    'manifest_entries': 2, 'files': {name: prepare_kit.digest(remote/name)
                        for name in ['aot/aot.json', 'MANIFEST']}}
            if corrupt:
                with self.assertRaisesRegex(ValueError, 'kit checksum mismatch'):
                    prepare_kit.prepare(source, output, spec)
                self.assertFalse(output.exists())
            else:
                result = prepare_kit.prepare(source, output, spec)
                self.assertEqual(result['verified_files'], 2)
                (output/'kernel').write_text('output-only change')
                self.assertEqual((source/'kernel').read_text(), 'preserved')
                with self.assertRaisesRegex(ValueError, 'already exists'):
                    prepare_kit.prepare(source, output, spec)
            self.assertEqual((source/'aot/aot.json').read_text(), 'old')
            self.assertFalse(list(root.glob('.kit-prepare-*')))


if __name__ == '__main__':
    unittest.main()
