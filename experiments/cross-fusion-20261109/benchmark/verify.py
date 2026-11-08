#!/usr/bin/env python3
"""Run every frozen cell against GMP for both builds without reading a clock."""
import argparse
import json
from pathlib import Path
import subprocess

from measure import require_runtime_dependencies, runtime_dependencies, sha, verify_build, verify_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest_path, build_path = args.manifest.resolve(), args.build.resolve()
    manifest = json.loads(manifest_path.read_text())
    build = json.loads(build_path.read_text())
    verify_build(build, manifest)
    verify_inputs(manifest_path.parent, manifest)
    args.output.mkdir(parents=True, exist_ok=False)
    output = args.output.resolve()
    report = dict(status="running", manifest_sha256=sha(manifest_path), build_sha256=sha(build_path),
                  checks=0, warmup_checks=0)
    raw = output / "checks.jsonl"
    try:
        report["loader_before"] = runtime_dependencies(build)
        require_runtime_dependencies(report["loader_before"])
        with raw.open("w") as stream:
            for index, cell in enumerate(manifest["cells"]):
                path = manifest_path.parent / cell["input"]
                if sha(path) != cell["input_sha256"]:
                    raise RuntimeError("input changed before cell")
                for label in ("baseline", "candidate"):
                    binary = build["binaries"][label]["path"]
                    for mode, count in (("check", "0"), ("warmup_check", "2")):
                        argv = [binary, mode, cell["op"], str(cell["n"]), str(cell["top"]),
                                str(path), str(cell["alias"]).lower(), count]
                        result = subprocess.run(argv, capture_output=True, timeout=180, env=build["runtime_environment"])
                        row = dict(cell=index, label=label, mode=mode, argv=argv, exit_code=result.returncode,
                                   stdout_hex=result.stdout.hex(), stderr_hex=result.stderr.hex(),
                                   input_sha256=cell["input_sha256"])
                        stream.write(json.dumps(row, sort_keys=True) + "\n")
                        stream.flush()
                        if result.returncode:
                            raise RuntimeError("untimed GMP check failed")
                        value = json.loads(result.stdout)
                        if (value.get("verified") is not True or value.get("n") != cell["n"]
                                or value.get("top") != cell["top"]):
                            raise RuntimeError("unexpected untimed GMP check output")
                        report["checks" if mode == "check" else "warmup_checks"] += 1
                if sha(path) != cell["input_sha256"]:
                    raise RuntimeError("input changed after cell")
        verify_inputs(manifest_path.parent, manifest)
        verify_build(build, manifest)
        report["loader_after"] = runtime_dependencies(build)
        require_runtime_dependencies(report["loader_after"])
        if report["loader_before"]["loader_config"] != report["loader_after"]["loader_config"]:
            raise RuntimeError("loader configuration changed during preflight")
        if sha(manifest_path) != report["manifest_sha256"] or sha(build_path) != report["build_sha256"]:
            raise RuntimeError("manifest or build changed during preflight")
        report["status"] = "pass"
    except Exception as error:
        report["status"] = "fail"
        report["failure"] = repr(error)
        raise
    finally:
        report["raw"] = str(raw)
        report["raw_sha256"] = sha(raw) if raw.exists() else None
        (output / "preflight.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
