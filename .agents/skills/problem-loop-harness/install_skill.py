#!/usr/bin/env python3
"""Install the reviewed package to an explicit new skill folder, without execution."""
import argparse
import hashlib
from pathlib import Path
import shutil


def install(source, destination):
    source = Path(source).resolve()
    destination = Path(destination).expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('Destination exists; inspect it before choosing a new destination')
    if destination.name != 'problem-loop-harness':
        raise ValueError('Destination folder must be named problem-loop-harness')
    files = []
    for line in (source / 'SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        path = Path(relative)
        if path.is_absolute() or '..' in path.parts or not path.parts:
            raise ValueError('Unsafe manifest path')
        current = source
        for part in path.parts:
            current /= part
            if current.is_symlink():
                raise ValueError('Symlink in package')
        if hashlib.sha256(current.read_bytes()).hexdigest() != digest:
            raise ValueError('Package hash mismatch: ' + relative)
        files.append(path)
    if Path('SKILL.md') not in files:
        raise ValueError('Missing skill entrypoint')
    destination.mkdir(parents=True, exist_ok=False)
    for path in files + [Path('SHA256SUMS')]:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / path, target)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', help='New Codex skill folder; parent location must be authorized')
    args = parser.parse_args()
    print(install(Path(__file__).parent, args.destination))
