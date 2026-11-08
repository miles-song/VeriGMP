#!/usr/bin/env python3
"""Run scoped semantic mutations on fresh copies of the pinned source commit."""
import hashlib
import io
import json
import pathlib
import re
import subprocess
import sys
import tarfile
import tempfile

MUTATIONS = [
    ("drop_input", "cross_limb", "(a as u128)+(b as u128)+(c as u128)+(carry as u128)",
     "(a as u128)+(b as u128)+(0 as u128)+(carry as u128)"),
    ("clip_carry", "cross_limb", "let next=(total/radix) as u64;",
     "let next=if total/radix>1 {1u64} else {(total/radix) as u64};"),
    ("wrong_sub_initial", "combine_cross", "    } else {\n        let mut carry=1u64;\n        while i<z2.len()",
     "    } else {\n        let mut carry=0u64;\n        while i<z2.len()"),
    ("wrong_sub_high", "combine_cross", "        carry-1\n    }\n}\n\n/// Add a slice",
     "        carry\n    }\n}\n\n/// Add a slice"),
    ("drop_z2", "combine_cross", "cross_limb(z0[i],z2[i],dst[i],carry)",
     "cross_limb(z0[i],0,dst[i],carry)"),
    ("wrong_tail_complement", "combine_cross", "cross_limb(z0[i],0,u64::MAX-dst[i],carry)",
     "cross_limb(z0[i],0,dst[i],carry)"),
    ("wrong_tail_extension", "combine_cross", "cross_limb(z0[i],0,dst[i],carry)",
     "cross_limb(z0[i],1,dst[i],carry)"),
]
if len(sys.argv) != 6:
    raise SystemExit("usage: mutations.py OUT COMMIT FAST_WORDS_SHA256 RLIB VIR")
out = pathlib.Path(sys.argv[1])
commit, expected_source, rlib, vir = sys.argv[2:]
out.mkdir(parents=True, exist_ok=False)
archive = subprocess.check_output(["git", "archive", "--format=tar", commit, "native"])
results = []
for name, function, before, after in MUTATIONS:
    with tempfile.TemporaryDirectory(prefix="verigmp-cross-mutant-") as tmp:
        root = pathlib.Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(root, filter="data")
        path = root / "native/verified/fast_words.rs"
        original = path.read_bytes()
        actual_source = hashlib.sha256(original).hexdigest()
        if actual_source != expected_source:
            raise RuntimeError(f"{name}: source does not match verified snapshot")
        text = original.decode("utf-8")
        if text.count(before) != 1:
            raise RuntimeError(f"{name}: anchor count {text.count(before)}")
        mutated = text.replace(before, after)
        path.write_text(mutated, encoding="utf-8")
        (out / f"{name}.rs").write_text(mutated, encoding="utf-8")
        command = ["verus", "native/fast_runner.rs", "--verify-only-module", "fast_words",
                   "--verify-function", function, "--no-cheating", "--rlimit", "2", "--num-threads", "1"]
        result = subprocess.run(command, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60)
        log = result.stdout.decode(errors="replace")
        (out / f"{name}.log").write_text(log, encoding="utf-8")
        summaries = re.findall(r"verification results:: (\d+) verified, (\d+) errors", log)
        diagnostics = ("postcondition not satisfied", "assertion failed", "invariant not satisfied",
                       "requires not satisfied", "precondition not satisfied")
        semantic = (result.returncode == 1 and len(summaries) == 1 and int(summaries[0][1]) > 0
                    and any(item in log for item in diagnostics)
                    and not any(item in log.lower() for item in ("resource limit", "timed out", "unexpected token")))
        row = {"name": name, "function": function, "exit": result.returncode,
               "summary": summaries, "semantic_rejection": semantic,
               "mutated_source_sha256": hashlib.sha256(mutated.encode()).hexdigest(), "command": command}
        results.append(row)
        print(json.dumps(row, sort_keys=True), flush=True)
        if not semantic:
            raise RuntimeError(f"{name}: no semantic rejection; inspect {out / (name + '.log')}")
identity = {"commit": commit, "fast_words_sha256": expected_source,
            "rlib_sha256": hashlib.file_digest(open(rlib, "rb"), "sha256").hexdigest(),
            "vir_sha256": hashlib.file_digest(open(vir, "rb"), "sha256").hexdigest()}
(out / "report.json").write_text(json.dumps({"identity": identity, "mutants": results}, indent=2) + "\n", encoding="utf-8")
