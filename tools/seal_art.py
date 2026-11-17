#!/usr/bin/env python3
"""Prepare encrypted art locally from private approved PNGs and a verified GRP."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from art_crypto import original_entry, read_grp, seal


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=True) + '\n')


def prepare(grp, source, recipes, output, pins):
    PINS = json.loads(Path(pins).read_text())
    if sha(grp) != PINS['files']['GFX.GRP']:
        raise ValueError('Unsupported original GFX.GRP')
    if output.exists():
        raise ValueError('Art output must be a new directory')
    entries = read_grp(grp)
    plan = json.loads(recipes.read_text())
    output.mkdir(parents=True)
    (output/'encrypted').mkdir()
    manifest = {}
    try:
        for name, row in plan['statics'].items():
            if 'file' not in row:
                continue
            relative = Path(row['file'])
            if relative.parent != Path('images') or relative.suffix != '.png' or '\\' in str(relative):
                raise ValueError('Invalid art source path')
            plain = (source/relative).read_bytes()
            if hashlib.sha256(plain).hexdigest() != row['sha256']:
                raise ValueError('Private art hash differs: '+name)
            row.setdefault('method', 'redraw')
            metadata, cipher = seal(name, original_entry(entries, name), plain)
            (output/'encrypted'/(name+'.enc')).write_bytes(cipher)
            manifest[name] = metadata
        write_json(output/'manifest.json', manifest)
        write_json(output/'recipes.json', plan)
    except Exception:
        shutil.rmtree(output)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--grp', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True, help='Private directory containing images/')
    parser.add_argument('--recipes', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pins', type=Path, required=True, help='builder/pins.json from the engine repository')
    args = parser.parse_args()
    prepare(args.grp, args.source, args.recipes, args.output, args.pins)
