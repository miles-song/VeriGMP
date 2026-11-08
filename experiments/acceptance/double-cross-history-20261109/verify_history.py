#!/usr/bin/env python3
"""Recover the historical double-cross branch in an isolated bare repository."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


MAIN = "338632fef7f0cbe5b442cc6b00b7161bebded647"
MAIN_TREE = "cbea0ab1dd217a81c56e8a2558bf6e6c86243d11"
BOUNDARY = "515f1efa0d79bcb73272df9f54917f156decf1e1"
TIP = "3ce342e2f09964518c9ff889b2538006c44741c0"
REF = "refs/heads/codex/verigmp-double-cross-20261108"
BUNDLE_SHA256 = "88b007fa20648ab061556d5219fe2c06e613172861488f73a2b57c03fa7a2f5a"
GRAPH = [
    ("5305c6b3d7052cc617f7ff9772b932026b26765a", "1d08fa13c51bf110668fd84cb0dd43e17d30e524", BOUNDARY),
    ("9fd574a8bf9d8481904241d7f59c7b40cd3531ca", "1e3f1d98512674044ad0d702d309698f26803736", "5305c6b3d7052cc617f7ff9772b932026b26765a"),
    ("7e5db4b61e8a6b9f1079be90081cabe2081ae1e8", "345b0f98aaa97bab76c88cc7a44f2f10728fb698", "9fd574a8bf9d8481904241d7f59c7b40cd3531ca"),
    ("f46b835cb8f812293924418abc42a39978d78694", "a2a18255218b3ae21fde586db7eec87f65fa1ac5", "7e5db4b61e8a6b9f1079be90081cabe2081ae1e8"),
    ("5e020923d41cabf7aae8ac513e7058fedcd50c6f", "49f197f2f83c1ab472d00f54246615315dc96635", "f46b835cb8f812293924418abc42a39978d78694"),
    ("e51ed428ed9e20a78150dd72af47a37057b2ac72", "70516e29c6c5843292f2ecb81f470dd5ea74a8b5", "5e020923d41cabf7aae8ac513e7058fedcd50c6f"),
    ("9c1d6f001520c382e117f3d86e488c71834e1bc7", "71f9ae8f20ea3e883bbc3fbcf9e39b7d77104c51", "e51ed428ed9e20a78150dd72af47a37057b2ac72"),
    (TIP, "eb63c089229bf15e2464a44fbdcccee177362aa5", "9c1d6f001520c382e117f3d86e488c71834e1bc7"),
]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


ENV = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
ENV.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"})


def run(*command, check=True):
    result = subprocess.run(command, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {command!r}\n{result.stdout}{result.stderr}")
    return result


def git(repo, *args, check=True):
    return run("git", "-C", str(repo), *args, check=check)


def verify(args):
    main_repo = args.main_repo.resolve(strict=True)
    fixture = args.fixture.resolve()
    bundle = Path(__file__).resolve().with_name("source.bundle")
    require(main_repo.is_dir(), "main repository must be a directory")
    require(not fixture.exists() and fixture.parent.is_dir(), "fixture must be a new path with an existing parent")
    require(main_repo not in fixture.parents and fixture not in main_repo.parents, "fixture must be outside the source repository")
    require(sha256(bundle) == BUNDLE_SHA256, "bundle SHA-256 differs from the registered value")
    require(git(main_repo, "rev-parse", f"{MAIN}^{{tree}}").stdout.strip() == MAIN_TREE, "source does not have the expected main tree")
    heads = run("git", "bundle", "list-heads", str(bundle)).stdout.strip()
    require(heads == f"{TIP} {REF}", "unexpected bundle ref")

    run("git", "init", "--bare", "--object-format=sha1", str(fixture))
    git(fixture, "-c", "protocol.file.allow=always", "fetch", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules", main_repo.as_uri(), f"+{MAIN}:refs/heads/main")
    require(git(fixture, "rev-parse", "refs/heads/main").stdout.strip() == MAIN, "fixture main differs")
    require(git(fixture, "rev-parse", f"{MAIN}^{{tree}}").stdout.strip() == MAIN_TREE, "fixture main tree differs")
    require(git(fixture, "merge-base", "--is-ancestor", BOUNDARY, MAIN, check=False).returncode == 0, "bundle prerequisite is not an ancestor of main")
    alternate_file = fixture / "objects" / "info" / "alternates"
    require(not alternate_file.exists(), "fixture has an alternates file before recovery")
    refs_before = git(fixture, "for-each-ref", "--format=%(objectname) %(refname)").stdout.splitlines()
    require(refs_before == [f"{MAIN} refs/heads/main"], "fixture contains refs other than main")
    absent_before = {commit: git(fixture, "cat-file", "-e", commit, check=False).returncode != 0 for commit, _, _ in GRAPH}
    require(all(absent_before.values()), "a candidate commit was already present in the main-only fixture")

    bundle_check = git(fixture, "bundle", "verify", str(bundle))
    git(fixture, "fetch", "--no-tags", "--no-write-fetch-head", "--no-recurse-submodules", str(bundle), f"+{REF}:refs/heads/recovered")
    require(not alternate_file.exists(), "fixture has an alternates file after recovery")
    require(git(fixture, "rev-parse", "refs/heads/recovered").stdout.strip() == TIP, "recovered tip differs")
    commits = git(fixture, "rev-list", "--reverse", "--topo-order", f"{MAIN}..{TIP}").stdout.splitlines()
    require(commits == [entry[0] for entry in GRAPH], "non-main commit sequence differs")
    observed_graph = []
    for commit, tree, parent in GRAPH:
        actual_tree, actual_parents = git(fixture, "show", "-s", "--format=%T%n%P", commit).stdout.splitlines()
        require((actual_tree, actual_parents) == (tree, parent), f"tree or parents differ for {commit}")
        observed_graph.append({"commit": commit, "tree": actual_tree, "parents": actual_parents.split()})
    objects = git(fixture, "rev-list", "--objects", "--missing=print", TIP).stdout.splitlines()
    require(not any(line.startswith("?") for line in objects), "recovered graph has missing objects")
    fsck = git(fixture, "fsck", "--full", "--no-reflogs")
    listing = git(fixture, "ls-tree", "-r", "--full-tree", TIP).stdout.encode("utf-8")
    refs_after = git(fixture, "for-each-ref", "--format=%(objectname) %(refname)").stdout.splitlines()
    require(refs_after == [f"{MAIN} refs/heads/main", f"{TIP} refs/heads/recovered"], "unexpected refs after recovery")

    return {
        "result": "PASS",
        "git_version": run("git", "--version").stdout.strip(),
        "python_version": sys.version,
        "source_main": MAIN,
        "source_main_tree": MAIN_TREE,
        "source_repository_uri": main_repo.as_uri(),
        "fixture": str(fixture),
        "bundle_sha256": BUNDLE_SHA256,
        "bundle_bytes": bundle.stat().st_size,
        "bundle_advertised_ref": heads,
        "bundle_verify_stdout": bundle_check.stdout,
        "bundle_verify_stderr": bundle_check.stderr,
        "prerequisite_ancestor_of_main": BOUNDARY,
        "refs_before": refs_before,
        "candidate_commits_absent_before": absent_before,
        "alternate_file_absent_before_and_after": True,
        "git_environment_sanitized": True,
        "refs_after": refs_after,
        "recovered_non_main_graph_oldest_first": observed_graph,
        "recovered_reachable_object_entries": len(objects),
        "missing_object_entries": 0,
        "fsck_exit_code": fsck.returncode,
        "fsck_stdout": fsck.stdout,
        "fsck_stderr": fsck.stderr,
        "tip_recursive_tree_entries": len(listing.splitlines()),
        "tip_recursive_tree_listing_sha256": hashlib.sha256(listing).hexdigest(),
        "verifier_sha256": sha256(Path(__file__).resolve()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--main-repo", required=True, type=Path, help="local Git repository containing the specified main commit")
    parser.add_argument("--fixture", required=True, type=Path, help="new path for the isolated bare repository; it is retained")
    parser.add_argument("--receipt", type=Path, help="new JSON receipt path")
    args = parser.parse_args()
    if args.receipt and args.receipt.exists():
        parser.error("receipt path already exists")
    try:
        receipt = json.dumps(verify(args), indent=2) + "\n"
        if args.receipt:
            args.receipt.write_text(receipt, encoding="utf-8", newline="\n")
        print(receipt, end="")
    except (OSError, RuntimeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
