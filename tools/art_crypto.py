"""Disc-bound redraws: RFC 5869 HKDF-SHA256 and libsodium XChaCha20-Poly1305."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import struct
from nacl.exceptions import CryptoError
from nacl.secret import Aead

SALT = b'Horke Leto Remastered art v1'


def hkdf(entry, salt, info):
    # RFC 5869 extract and the first expand block (our key is exactly 32 bytes).
    return hmac.digest(hmac.digest(salt, entry, 'sha256'), info + b'\x01', 'sha256')


def context(name):
    if not re.fullmatch(r'[A-Z0-9_!@.+-]{1,14}', name) or not name.endswith('.FLC'):
        raise ValueError('Invalid original asset name')
    return b'FLC redraw\x00' + name.encode('ascii')


def seal(name, entry, plaintext):
    aad = context(name)
    nonce = os.urandom(Aead.NONCE_SIZE)
    cipher = Aead(hkdf(entry, SALT, aad)).encrypt(plaintext, aad, nonce).ciphertext
    return dict(original_entry_sha256=hashlib.sha256(entry).hexdigest(), nonce=nonce.hex(),
                ciphertext_sha256=hashlib.sha256(cipher).hexdigest(),
                plaintext_sha256=hashlib.sha256(plaintext).hexdigest()), cipher


def unseal(name, entry, row, cipher):
    aad = context(name)
    if hashlib.sha256(entry).hexdigest() != row['original_entry_sha256']:
        raise ValueError('Original entry differs: ' + name)
    if hashlib.sha256(cipher).hexdigest() != row['ciphertext_sha256']:
        raise ValueError('Ciphertext hash differs: ' + name)
    try:
        plain = Aead(hkdf(entry, SALT, aad)).decrypt(cipher, aad, bytes.fromhex(row['nonce']))
    except (CryptoError, ValueError) as error:
        raise ValueError('Art authentication failed: ' + name) from error
    if hashlib.sha256(plain).hexdigest() != row['plaintext_sha256']:
        raise ValueError('Plaintext hash differs: ' + name)
    return plain


def read_grp(path):
    data = Path(path).read_bytes()
    if len(data) < 44 or data[:16] != b'AGDS group file\x1a':
        raise ValueError('Invalid GRP header')
    header, magic, version, used, capacity = struct.unpack_from('<IIIII', data, 16)
    payload = 44 + capacity * 30
    if (header, magic, version) != (44, 0x1a03c9e6, 1) or used > capacity or payload > len(data):
        raise ValueError('Invalid GRP directory')
    entries = {}
    for index in range(used):
        position = 44 + index * 30
        raw = data[position:position+14].split(b'\x00', 1)[0]
        if not raw or any(c < 32 or c > 126 or c in b'/\\:' for c in raw) or raw in (b'.', b'..'):
            raise ValueError('Invalid GRP member name')
        name = raw.decode('ascii').upper()
        offset, size = struct.unpack_from('<II', data, position+14)
        if offset < payload or offset + size > len(data) or name in entries:
            raise ValueError('Invalid GRP member bounds or duplicate: ' + name)
        entries[name] = data[offset:offset+size]
    return entries


def original_entry(entries, name):
    if name not in entries:
        raise ValueError('Original entry missing: ' + name)
    return entries[name]


def decrypt_art(art, grp, destination):
    """Write authenticated plaintext only to the player's private build directory."""
    rows = json.loads((art/'manifest.json').read_text())
    recipes = json.loads((art/'recipes.json').read_text())
    entries = read_grp(grp)
    stage = destination.with_name(destination.name + '.stage')
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    try:
        for name, row in recipes['statics'].items():
            if 'file' not in row:
                continue
            relative = Path(row['file'])
            if relative.parent != Path('images') or relative.suffix != '.png' or '\\' in str(relative):
                raise ValueError('Invalid art output path')
            target = stage/relative
            target.parent.mkdir(exist_ok=True)
            if name in rows:
                meta = rows[name]
                if meta['plaintext_sha256'] != row['sha256']:
                    raise ValueError('Art recipe hash differs: ' + name)
                plain = unseal(name, original_entry(entries, name), meta, (art/'encrypted'/(name+'.enc')).read_bytes())
            else:
                raise ValueError('Missing encrypted art: ' + name)
            if hashlib.sha256(plain).hexdigest() != row['sha256']:
                raise ValueError('Art hash differs: ' + name)
            target.write_bytes(plain)
        (stage/'manifest.json').write_text(json.dumps(recipes, indent=2, ensure_ascii=True)+'\n')
        if destination.exists():
            shutil.rmtree(destination)
        stage.rename(destination)
    except Exception:
        shutil.rmtree(stage)
        raise
    return destination
