#!/usr/bin/env python3
"""Restore the exact-by3 history into a new, isolated main-only repository."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


MAIN = "2d4e1748e5efe9143c21b13b53dbf6ebf1fffaba"
MAIN_TREE = "6b6e9c4247bace1506303da5acbaa55edfa87354"
BOUNDARY = "4510b46e4010dd287c9cf760f0195f2edc32e1f7"
TIP = "2010bd4a025d7cdf22e153a5e198f2f33b43cf77"
REF = "refs/heads/codex/gmp-exact-by3-20261109"
BUNDLE_SHA256 = "15969149016acd56d7c8344dcce58679381af3b0a00b9f6ad573479adfa1e648"
GRAPH = [
    ("c28039e165e082fdcff7ab3ed72eb32252d0153e", "eec8663782d01d4bd61cd1b0f6622aceccd37899", BOUNDARY),
    ("d5acf5ba17b32993ea0272aa9b17669412cd688b", "988c46ae554a1e10a0a356f3018d2568e9f2ff85", "c28039e165e082fdcff7ab3ed72eb32252d0153e"),
    ("27f0e42188e3ecbcb6263ee9a4278e763e0da3a1", "17dc86851b82dc5d68dc8cf0140ffa257f765d00", "d5acf5ba17b32993ea0272aa9b17669412cd688b"),
    (TIP, "3cc25bdec266408e012ffff9641e767d854474bd", "27f0e42188e3ecbcb6263ee9a4278e763e0da3a1"),
]
FILES = {
    "native/specs/exact_by3.rs": "08b7913b202a5d26fa4e7444a12e1a454cf3c561df24195fabf44cef1eeb4b44",
    "native/verified/exact_by3.rs": "9466ce3e36310971768f1742707ae0960bb0b05222ba607935e3d26a3db2e253",
    "native/verified/toom_interpolate.rs": "f288b666feb11ffc815df3de66b8522dfe05f87178f9cbdaa2d92f9cd95242db",
    "experiments/acceptance/exact-by3-20261109/static-d5acf5b/evidence.zip": "69ff54aa4c8e56979e1d6936efa8dad15c424e210e20d6b4693e851d6f5e2348",
}
STATIC = "experiments/acceptance/exact-by3-20261109/static-d5acf5b"
REFERENCE = "experiments/exact-by3-20261109"

ENV = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
ENV.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def run(*command, check=True):
    result = subprocess.run(command, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n"
                           + result.stderr.decode("utf-8", "replace"))
    return result


def git(repo, *args, check=True):
    return run("git", "-C", str(repo), *args, check=check)


def text(result):
    return result.stdout.decode("utf-8").strip()


def verify(args):
    source = args.main_source
    local_source = None
    if "://" not in source and not source.startswith("git@"):
        local_source = Path(source).resolve(strict=True)
        source = local_source.as_uri()
    fixture = args.fixture.resolve()
    checkout = fixture.with_name(fixture.name + "-checkout")
    bundle = Path(__file__).resolve().with_name("source.bundle")
    require(not fixture.exists() and not checkout.exists() and fixture.parent.is_dir(),
            "fixture and fixture-checkout must be new paths with an existing parent")
    if local_source:
        require(local_source not in fixture.parents and fixture not in local_source.parents,
                "fixture must be outside the source repository")
    require(sha256(bundle.read_bytes()) == BUNDLE_SHA256, "bundle SHA-256 differs")
    heads = text(run("git", "bundle", "list-heads", str(bundle)))
    require(heads == f"{TIP} {REF}", "unexpected bundle ref")

    run("git", "init", "--bare", "--object-format=sha1", str(fixture))
    git(fixture, "symbolic-ref", "HEAD", "refs/heads/main")
    git(fixture, "-c", "protocol.file.allow=always", "fetch", "--no-tags",
        "--no-write-fetch-head", "--no-recurse-submodules", source, f"+{MAIN}:refs/heads/main")
    require(text(git(fixture, "rev-parse", "refs/heads/main")) == MAIN, "fixture main differs")
    require(text(git(fixture, "rev-parse", f"{MAIN}^{{tree}}")) == MAIN_TREE, "main tree differs")
    require(git(fixture, "merge-base", "--is-ancestor", BOUNDARY, MAIN, check=False).returncode == 0,
            "bundle prerequisite is not an ancestor of main")
    alternate = fixture / "objects" / "info" / "alternates"
    require(not alternate.exists(), "fixture has an alternates file")
    refs_before = text(git(fixture, "for-each-ref", "--format=%(objectname) %(refname)")).splitlines()
    require(refs_before == [f"{MAIN} refs/heads/main"], "fixture contains other refs")
    main_objects = set(text(git(fixture, "rev-list", "--objects", "--no-object-names", MAIN)).splitlines())
    initial_objects = set(text(git(fixture, "cat-file", "--batch-all-objects", "--batch-check=%(objectname)")).splitlines())
    require(initial_objects == main_objects, "fixture has missing or non-main objects before recovery")
    absent = {commit: git(fixture, "cat-file", "-e", commit, check=False).returncode != 0
              for commit, _, _ in GRAPH}
    require(all(absent.values()), "candidate commits were present before bundle recovery")

    bundle_check = git(fixture, "bundle", "verify", str(bundle))
    git(fixture, "fetch", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules",
        str(bundle), f"+{REF}:refs/heads/recovered")
    require(not alternate.exists(), "fixture has an alternates file after recovery")
    require(text(git(fixture, "rev-parse", "refs/heads/recovered")) == TIP, "tip differs")
    commits = text(git(fixture, "rev-list", "--reverse", "--topo-order", f"{MAIN}..{TIP}")).splitlines()
    require(commits == [entry[0] for entry in GRAPH], "non-main commit sequence differs")
    observed_graph = []
    for commit, tree, parent in GRAPH:
        actual_tree, actual_parent = text(git(fixture, "show", "-s", "--format=%T%n%P", commit)).splitlines()
        require((actual_tree, actual_parent) == (tree, parent), f"tree or parent differs for {commit}")
        observed_graph.append({"commit": commit, "tree": tree, "parent": parent})
    objects = text(git(fixture, "rev-list", "--objects", "--missing=print", TIP)).splitlines()
    require(not any(line.startswith("?") for line in objects), "recovered graph has missing objects")
    fsck = git(fixture, "fsck", "--full", "--no-reflogs")
    refs_after = text(git(fixture, "for-each-ref", "--format=%(objectname) %(refname)")).splitlines()
    require(refs_after == [f"{MAIN} refs/heads/main", f"{TIP} refs/heads/recovered"], "unexpected refs")

    checkout.mkdir()
    git(fixture, f"--work-tree={checkout}", "-c", "core.autocrlf=false", "-c", "core.longpaths=true", "checkout", TIP, "--", ".")
    require(git(fixture, f"--work-tree={checkout}", "-c", "core.autocrlf=false", "-c", "core.longpaths=true", "diff-files", "--quiet", check=False).returncode == 0,
            "restored checkout differs from its index")
    require(git(fixture, "diff-index", "--cached", "--quiet", TIP, check=False).returncode == 0,
            "restored index differs from the candidate tree")
    observed_files = {}
    for path, expected in FILES.items():
        data = (checkout / path).read_bytes()
        require(sha256(data) == expected, f"restored file hash differs: {path}")
        require(git(fixture, "show", f"{TIP}:{path}").stdout == data, f"checkout differs from blob: {path}")
        observed_files[path] = {"sha256": expected, "bytes": len(data)}

    reference = checkout / REFERENCE
    reference_info = json.loads((reference / "reference.json").read_text(encoding="utf-8"))
    licenses = {}
    for name in ("COPYING.LESSERv3", "COPYINGv2", "COPYINGv3"):
        data = (reference / "reference" / name).read_bytes()
        expected = reference_info["members"][name]
        require(len(data) == expected["bytes"] and sha256(data) == expected["sha256"],
                f"reference license differs: {name}")
        licenses[name] = expected["sha256"]
    require((reference / "reference" / "NOTICE.md").is_file(), "reference notice is missing")

    checker = checkout / STATIC / "check_evidence.py"
    result = run(sys.executable, "-I", str(checker), "--check-publication")
    static = json.loads(result.stdout)
    require(static["status"] == "pass" and static["publication_checked"] is True,
            "restored static evidence checker did not pass")
    require(static["archive_sha256"] == FILES[f"{STATIC}/evidence.zip"] and static["archive_members"] == 1209,
            "unexpected static archive identity")
    require(static["performance_accepted"] is False, "unexpected static performance status")
    listing = git(fixture, "ls-tree", "-r", "--full-tree", TIP).stdout
    return {
        "result": "PASS",
        "git_version": text(run("git", "--version")),
        "python_version": sys.version,
        "main_source": source,
        "source_main": MAIN,
        "source_main_tree": MAIN_TREE,
        "fixture": str(fixture),
        "checkout": str(checkout),
        "bundle_sha256": BUNDLE_SHA256,
        "bundle_bytes": bundle.stat().st_size,
        "bundle_advertised_ref": heads,
        "bundle_verify_stdout": bundle_check.stdout.decode("utf-8"),
        "prerequisite_ancestor_of_main": BOUNDARY,
        "refs_before": refs_before,
        "initial_object_count": len(initial_objects),
        "initial_objects_equal_main_reachable": True,
        "candidate_commits_absent_before": absent,
        "alternate_file_absent_before_and_after": True,
        "git_environment_sanitized": True,
        "refs_after": refs_after,
        "recovered_non_main_graph_oldest_first": observed_graph,
        "recovered_reachable_object_entries": len(objects),
        "missing_object_entries": 0,
        "fsck_exit_code": fsck.returncode,
        "checkout_matches_recovered_tree": True,
        "restored_file_hashes": observed_files,
        "reference_license_hashes": licenses,
        "reference_notice_present": True,
        "restored_static_checker": static,
        "tip_recursive_tree_entries": len(listing.splitlines()),
        "tip_recursive_tree_listing_sha256": sha256(listing),
        "verifier_sha256": sha256(Path(__file__).resolve().read_bytes()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-source", default="https://github.com/miles-song/VeriGMP.git",
                        help="public Git URL or local repository containing the specified main commit")
    parser.add_argument("--fixture", required=True, type=Path,
                        help="new path for an isolated bare repository; a sibling -checkout is also retained")
    parser.add_argument("--receipt", type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    if args.receipt and args.receipt.exists():
        parser.error("receipt path already exists")
    try:
        receipt = json.dumps(verify(args), indent=2) + "\n"
        if args.receipt:
            args.receipt.write_text(receipt, encoding="utf-8", newline="\n")
        print(receipt, end="")
    except (OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
