#!/usr/bin/env python3
"""Prepare a separate checksum-verified kit; never modify or activate the input kit."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def child(root, name):
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError(f'invalid kit path: {name}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'kit path escapes directory: {name}')
    return path


def prepare(source, output, spec):
    source, output = source.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('output already exists; preserve it and choose a new path')
    if output.resolve().is_relative_to(source):
        raise ValueError('output must be outside the input kit')
    if digest(source / 'aot/aot.json') != spec['base_aot_sha256']:
        raise ValueError('input kit metadata differs from the pinned base')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.kit-prepare-', dir=output.parent) as temp:
        staged = Path(temp) / 'kit'
        # Independent copies: later edits to either kit cannot alter the other.
        shutil.copytree(source, staged)
        for name, expected in spec['files'].items():
            target = child(staged, name)
            with urllib.request.urlopen(spec['url'] + name, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'upstream checksum mismatch: {name}')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        entries = (staged / 'MANIFEST').read_text().splitlines()
        if len(entries) != spec['manifest_entries']:
            raise ValueError('unexpected manifest entry count')
        for line in entries:
            expected, name = line.split(maxsplit=1)
            if digest(child(staged, name)) != expected:
                raise ValueError(f'kit checksum mismatch: {name}')
        if output.exists() or output.is_symlink():
            raise ValueError('output appeared during preparation; preserving it')
        staged.rename(output)
    return {'revision': spec['revision'], 'verified_files': len(entries),
            'aot_sha256': digest(output / 'aot/aot.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True, help='original pinned kit directory')
    parser.add_argument('--output', type=Path, required=True, help='new inactive kit directory')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'lock.json').read_text())['kit_overlay']
    print(json.dumps(prepare(args.base, args.output, spec), indent=2))


if __name__ == '__main__':
    main()
