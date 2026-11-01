#!/usr/bin/env python3
"""Install the pinned verifier archive locally; does not alter shell profiles.

Rustup must already provide native/toolchain.json's Rust version. On this
workspace it lives in deps/cargo and deps/rustup; CI uses its supplied rustup.
"""
import hashlib
import json
from pathlib import Path
import platform
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if platform.system() != 'Linux' or platform.machine() not in ('x86_64','AMD64'):
        raise SystemExit('This pinned bootstrap supports x86_64 Linux (including WSL).')
    pin = json.loads((ROOT/'native/toolchain.json').read_text())
    archive = ROOT/'deps/verus-download'/pin['archive']
    archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():
        temporary = archive.with_suffix('.partial')
        request = urllib.request.Request(pin['url'],headers={'User-Agent':'verigmp-verifier'})
        with urllib.request.urlopen(request,timeout=60) as response, temporary.open('wb') as output:
            shutil.copyfileobj(response,output)
        temporary.replace(archive)
    with archive.open('rb') as source:
        if hashlib.file_digest(source,'sha256').hexdigest() != pin['sha256']:
            raise SystemExit('Verifier archive SHA-256 mismatch')
    target = ROOT/'deps/verus'
    with zipfile.ZipFile(archive) as source:
        for member in source.infolist():
            resolved = (target/member.filename).resolve()
            if not resolved.is_relative_to(target.resolve()):
                raise SystemExit('Archive path escapes local verifier directory')
        source.extractall(target)
        for member in source.infolist():
            if not member.is_dir() and (member.external_attr >> 16) & 0o111:
                (target/member.filename).chmod((member.external_attr >> 16) & 0o777)
    print(target/'verus-x86-linux/verus')


if __name__ == '__main__':
    main()
