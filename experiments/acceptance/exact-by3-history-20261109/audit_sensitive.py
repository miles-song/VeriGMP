#!/usr/bin/env python3
"""Scan recovered non-main objects and ZIP members for common credential markers."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


MAIN = "2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba"
TIP = "2010bd4a025d7cdf22e153a5e198f2f33b43cf77"
PATTERNS = {
    "private_key_header": rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----",
    "github_token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "gitlab_token": rb"\bglpat-[A-Za-z0-9_-]{20,}\b",
    "slack_token": rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b",
    "aws_access_key": rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    "openai_style_key": rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b",
    "bearer_literal": rb"(?i)\bBearer\s+[A-Za-z0-9._~+/-]{30,}={0,2}",
    "credential_assignment": rb"(?i)[\"'](?:password|passwd|secret|secret_key|api_key|access_token|refresh_token|private_key)[\"']\s*:\s*[\"'][^\"'\r\n]{12,}[\"']",
}
REGEXES = {name: re.compile(pattern) for name, pattern in PATTERNS.items()}
NAME_PATTERN = re.compile(r"(?i)(?:^|/)(?:\.env(?:\.[^/]*)?|id_(?:rsa|dsa|ecdsa|ed25519)|credentials\.json|auth\.json|[^/]+\.(?:pem|p12|pfx|key))$")
ENV = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
ENV.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull})


def git(repo, *args, input_data=None):
    result = subprocess.run(["git", "-C", str(repo), *args], input=input_data, env=ENV,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace"))
    return result.stdout


def audit(repo):
    objects = git(repo, "rev-list", "--objects", f"{TIP}", f"^{MAIN}").decode("utf-8").splitlines()
    names = {}
    for line in objects:
        oid, _, name = line.partition(" ")
        names[oid] = name
    payload = git(repo, "cat-file", "--batch", input_data=("\n".join(names) + "\n").encode("ascii"))
    stream = io.BytesIO(payload)
    findings = []
    blob_count = 0
    zip_count = 0
    member_count = 0
    bytes_scanned = 0

    def scan(label, data, depth=0):
        nonlocal zip_count, member_count, bytes_scanned
        bytes_scanned += len(data)
        for name, pattern in REGEXES.items():
            if pattern.search(data):
                findings.append({"location": label, "marker": name})
        if zipfile.is_zipfile(io.BytesIO(data)):
            if depth >= 3:
                raise RuntimeError("nested ZIP depth exceeds audit limit")
            zip_count += 1
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    if member.is_dir():
                        continue
                    member_count += 1
                    member_label = label + "!" + member.filename
                    if NAME_PATTERN.search(member.filename):
                        findings.append({"location": member_label, "marker": "credential_filename"})
                    scan(member_label, archive.read(member), depth + 1)

    for oid in names:
        header = stream.readline().decode("ascii").strip().split()
        if len(header) != 3 or header[0] != oid:
            raise RuntimeError(f"unexpected object header for {oid}")
        kind, size = header[1], int(header[2])
        data = stream.read(size)
        if len(data) != size or stream.read(1) != b"\n":
            raise RuntimeError(f"short object: {oid}")
        label = names[oid] or oid
        if NAME_PATTERN.search(label):
            findings.append({"location": label, "marker": "credential_filename"})
        if kind in ("blob", "commit"):
            blob_count += kind == "blob"
            scan(label, data)
    if stream.read(1):
        raise RuntimeError("unexpected trailing object data")
    return {
        "result": "PASS" if not findings else "FINDINGS",
        "scope": "objects reachable from candidate tip and not public main, including recursively scanned ZIP members",
        "candidate_tip": TIP,
        "public_main": MAIN,
        "git_objects": len(names),
        "git_blobs": blob_count,
        "zip_archives": zip_count,
        "zip_file_members": member_count,
        "bytes_scanned_including_archive_and_members": bytes_scanned,
        "patterns": sorted(REGEXES) + ["credential_filename"],
        "findings": findings,
        "scanner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path, help="isolated recovered repository")
    parser.add_argument("--receipt", type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    if args.receipt and args.receipt.exists():
        parser.error("receipt path already exists")
    try:
        report = audit(args.repo.resolve(strict=True))
        output = json.dumps(report, indent=2) + "\n"
        if args.receipt:
            args.receipt.write_text(output, encoding="utf-8", newline="\n")
        print(output, end="")
        return 0 if report["result"] == "PASS" else 1
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
