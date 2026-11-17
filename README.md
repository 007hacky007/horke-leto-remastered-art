# Horké léto Remastered - art

This is the redrawn artwork for
[Horké léto Remastered](https://github.com/007hacky007/horke-leto-remastered).
You do not need to download anything from here yourself. The builder fetches it
for you while it makes your playable copy.

**Everything here is locked.** Each of the 318 pictures (316 redrawn scenes,
the new exit screen and the inventory grid) is encrypted with a key that only
exists on an original Horké léto CD. Without the disc the files are useless, and
nothing readable is stored here.

## How the lock works

For each redraw, the builder reads the original picture with the same name from
`GFX.GRP` on your disc and checks its SHA-256 against `manifest.json`. The bytes
of that original picture are the input to HKDF-SHA256 (RFC 5869), with the salt
`Horke Leto Remastered art v1` and the info `FLC redraw`, a zero byte and the
picture's name in upper case. The resulting 32-byte key opens the file with
XChaCha20-Poly1305 (the libsodium IETF construction, with the same info as
additional data). If a picture on the disc is missing or different, the build
stops and names it.

- `encrypted/NAME.FLC.enc`: ciphertext with the 16-byte tag appended.
- `manifest.json`: for every redraw, the hash of the original picture, the
  nonce, and hashes of the ciphertext and of the unlocked PNG. It contains no
  keys and no original bytes.
- `recipes.json`: which redraw belongs to which animation frames, the fallback
  pictures and the colour grade used for the upscaled animations.

## Making a release archive

```
python3 tools/release.py --output Horke-Leto-Remastered-art-v0.1.0.zip
```

The archive is deterministic. The engine builder pins its SHA-256, so a new art
release also needs a new builder release. `tools/seal_art.py` encrypts a new set
of redraws from a private folder (it needs PyNaCl and the original `GFX.GRP`).
