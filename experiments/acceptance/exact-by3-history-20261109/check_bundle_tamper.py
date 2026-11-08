#!/usr/bin/env python3
"""Check that a damaged bundle is rejected before creating a fixture."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    if args.receipt and args.receipt.exists():
        parser.error("receipt path already exists")
    archive = Path(__file__).resolve().parent
    verifier = archive / "verify_history.py"
    bundle = archive / "source.bundle"
    with tempfile.TemporaryDirectory(prefix="exactby3-bundle-tamper-") as directory:
        temp = Path(directory)
        shutil.copyfile(verifier, temp / verifier.name)
        shutil.copyfile(bundle, temp / bundle.name)
        damaged = temp / bundle.name
        with damaged.open("r+b") as stream:
            stream.seek(-1, 2)
            byte = stream.read(1)
            stream.seek(-1, 2)
            stream.write(bytes([byte[0] ^ 1]))
        fixture = temp / "fixture.git"
        result = subprocess.run([sys.executable, "-I", str(temp / verifier.name), "--fixture", str(fixture)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        if result.returncode == 0 or "bundle SHA-256 differs" not in result.stderr or fixture.exists():
            raise RuntimeError("damaged bundle was not rejected before fixture creation")
        report = {
            "result": "PASS",
            "python_version": sys.version,
            "verifier_sha256": sha256(verifier),
            "original_bundle_sha256": sha256(bundle),
            "damaged_bundle_sha256": sha256(damaged),
            "returncode": result.returncode,
            "stderr": result.stderr.strip(),
            "fixture_created": fixture.exists(),
            "checker_sha256": sha256(Path(__file__).resolve()),
        }
    output = json.dumps(report, indent=2) + "\n"
    if args.receipt:
        args.receipt.write_text(output, encoding="utf-8", newline="\n")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
