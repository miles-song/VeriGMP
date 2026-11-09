#!/usr/bin/env python3
"""Cheap source/fixture/order checks only. Never invokes Verus, builds or timing."""
import argparse
import ast
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
FEATURE = Path(__file__).resolve().parent
BASE = "4510b46e4010dd287c9cf760f0195f2edc32e1f7"
NATIVE_TREE = "72dc8a5da2cbb7eddcdd26c219d50770e8b73b06"
CORE = ("native/verified/toom_interpolate.rs","native/verified/toom_words.rs")
from oracle import generate, static_witnesses
from mutations import check_anchors
from summarize import adjudicate
from test_raw_validate import self_check as raw_validator_self_check
sys.path.insert(0,str(ROOT/"experiments/packed-convolution"))
from layout_verify import git_adapter
from verus_logs import self_check


def git(*args):
    return subprocess.check_output(git_adapter()+list(args),timeout=60)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def manifest_hash(mapping):
    return sha(json.dumps(mapping,sort_keys=True,separators=(",",":")).encode())


def schedule(op,n):
    """Only interpolation visits, derived from the unchanged source schedule."""
    result = Counter()
    def toom(m):
        if m <= 192:
            return
        k = (m+2)//3
        result[2*(k+1)] += 1
        for child in (k,m-2*k,k+1,k+1,k+1):
            toom(child)
    def low(m,kind,limit,split):
        if m <= limit:
            return
        h = (9*m)//40 if split == 2 else (11*m)//36
        k = m-h
        if kind != "fast":
            toom(k)
        if kind == "square":
            low(h,"toom",limit,split)
        else:
            low(h,kind,limit,split)
            low(h,kind,limit,split)
    if op == 1:
        low(n,"fast",64,1) if n < 512 else low(n,"toom",128,2)
    elif op == 2:
        low(n,"square",64,1)
    else:
        assert op == 0
    return dict(sorted(result.items()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--require-clean",action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise RuntimeError("use a fresh external preflight directory")
    out.mkdir(parents=True)
    report = dict(status="running",verus_executed=False,native_build_executed=False,timing_executed=False)
    try:
        status = git("status","--porcelain").decode()
        if args.require_clean and status.strip():
            raise RuntimeError("source-ready acceptance requires clean committed inputs")
        names = git("ls-tree","-r","--name-only",BASE,"native").decode().splitlines()
        original = {name:git("show",BASE+":"+name) for name in names}
        current = {name:(ROOT/name).read_bytes() for name in names}
        changed = sorted(name for name in names if original[name] != current[name])
        assert changed == list(CORE), changed
        assert git("rev-parse",BASE+":native").decode().strip() == NATIVE_TREE
        before = original[CORE[1]].decode()
        after = current[CORE[1]].decode()
        insertion_start = after.index("pub open spec fn shift_factor")
        insertion_end = after.index("pub fn scale_exact",insertion_start)
        assert after[:insertion_start]+after[insertion_end:] == before
        helper = after[insertion_start:insertion_end]
        assert helper.count("while i<dst.len()") == 1
        assert not re.search(r"\b(?:unsafe|assume|admit|axiom)\b|external_body|Vec|vec!|alloc|copy_pad|scale_exact",helper)
        expected = original[CORE[0]].decode().replace(
            "    toom_words::copy_pad(scratch,z4);toom_words::scale_exact(scratch,16);\n"
            "    toom_words::sub_exact(p2,z0);toom_words::sub_exact(p2,scratch);",
            "    toom_words::sub_exact(p2,z0);toom_words::sub_shifted_exact(p2,z4,4);")
        expected = expected.replace(
            "    toom_words::copy_pad(scratch,pm);toom_words::scale_exact(scratch,2);\n"
            "    toom_words::sub_exact(p2,scratch);",
            "    toom_words::sub_shifted_exact(p2,pm,1);")
        assert current[CORE[0]].decode() == expected
        native = {name:sha(data) for name,data in current.items()}
        baseline = {name:sha(data) for name,data in original.items()}
        inputs = [*FEATURE.glob("*.py"),*FEATURE.glob("*.rs"),*FEATURE.glob("*.md"),
                  ROOT/"AGENTS.md",ROOT/"experiments/packed-convolution/layout_verify.py",
                  ROOT/"experiments/packed-convolution/verus_logs.py",
                  ROOT/"experiments/combination-20261108/codegen.py",
                  ROOT/"experiments/arithmetic-precondition-checks-20261108/bench.rs",
                  ROOT/"experiments/arithmetic-precondition-checks-20261108/measure.py"]
        for path in inputs:
            if path.suffix == ".py":
                ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        source = dict(head=git("rev-parse","HEAD").decode().strip(),
                      tree=git("rev-parse","HEAD^{tree}").decode().strip(),
                      base=BASE,baseline_native_tree=NATIVE_TREE,working_status=status,
                      native_sha256=native,baseline_sha256=baseline,
                      native_manifest_sha256=manifest_hash(native),
                      baseline_manifest_sha256=manifest_hash(baseline),
                      inputs_sha256={p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(set(inputs))})
        if args.require_clean:
            for name,digest in native.items():
                assert sha(git("show",source["head"]+":"+name)) == digest
            for name,digest in source["inputs_sha256"].items():
                assert sha(git("show",source["head"]+":"+name)) == digest
        diff = git("diff",BASE,"--",*CORE)
        (out/"core.diff").write_bytes(diff)
        report["source"] = dict(source,core_diff_sha256=sha(diff))
        shapes = json.loads(current["native/performance-target.json"])["key_shapes"]["shapes"]
        spec = importlib.util.spec_from_file_location("registered_measure",ROOT/"experiments/arithmetic-precondition-checks-20261108/measure.py")
        measure = importlib.util.module_from_spec(spec);spec.loader.exec_module(measure)
        cells = [(0,n,64) for n in measure.FULL_SIZES]+[(op,n,top) for op in (1,2) for n,top in shapes]
        assert len(cells) == 86 and len(set(cells)) == 86
        primary = {(1,n,63) for n in (512,513,1023,1024,1025,2048,4096)}
        primary |= {(2,n,63) for n in (511,512,513,1023,1024,1025,2048,4096)}
        schedules = []
        for i,cell in enumerate(cells):
            visits = schedule(cell[0],cell[1])
            assert bool(visits) == (cell in primary), cell
            lengths = sum(length*count for length,count in visits.items())
            schedules.append(dict(cell=cell,interpolation_lengths=visits,primary=cell in primary,
                deleted_loop_visits=4*lengths,deleted_scratch_stores=4*lengths,deleted_scratch_reads=4*lengths))
            for rep in range(7):
                order = measure.sample_paths(i,rep)
                assert sorted(order) == ["baseline","candidate","gmp"]
                assert (order.index("baseline") < order.index("candidate")) == (rep % 2 == 0)
                assert order.index("gmp") == ((i+rep) % 3)
        report["analytic_schedule"] = dict(basis="unchanged source control schedule; not dynamic instrumentation or checked cost theorem",
            primary_cells=sorted(primary),control_cells=len(cells)-len(primary),rows=schedules)
        report["harness"] = dict(cells=86,order_fixtures=86*7,calibrations_per_run=258,accepted_samples_per_run=1806,
                                 process_per_invocation=True,seed=measure.SEED)
        def synthetic(primary_ratio=0.97,regression=None):
            rows = []
            for key in cells:
                ratio = primary_ratio if key in primary else 1.0
                if key == regression:
                    ratio = 1.06
                rows.append(dict(op=key[0],n=key[1],top=key[2],
                    median_ns=dict(baseline=100.0,candidate=100.0*ratio,gmp=50.0),candidate_over_baseline=ratio))
            return adjudicate(rows,set(cells))
        assert synthetic()["performance_pass"]
        assert not synthetic(1.01)["primary_pass"]
        assert not synthetic(regression=(0,1,64))["all_86_pass"]
        assert synthetic()["performance_pass"] and not synthetic(1.01)["performance_pass"]
        report["adjudicator_synthetic_self_check"] = dict(status="pass",fixtures=4,measurements_executed=False)
        report["raw_validator_synthetic_self_check"] = raw_validator_self_check()
        report["semantic_mutant_anchors"] = check_anchors(ROOT/"native")
        report["strict_classifier_self_check"] = self_check()
        report["static_integer_witnesses"] = static_witnesses(shapes)
        report["oracle"] = generate(out/"oracle",shapes)
        report["tools"] = dict(python=sys.version,python_executable=sys.executable,
            python_sha256=sha(Path(sys.executable).read_bytes()),git_executable=shutil.which("git"),
            git_sha256=sha(Path(shutil.which("git")).read_bytes()))
        report["status"] = "source_ready"
    except BaseException as error:
        report.update(status="fail",failure=repr(error))
        raise
    finally:
        (out/"preflight.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=report["status"],source=source["head"],native_manifest_sha256=source["native_manifest_sha256"],
        oracle_cases=report["oracle"]["cases"],primary_cells=15,benchmark_executed=False,
        report_sha256=sha((out/"preflight.json").read_bytes())),indent=2))


if __name__ == "__main__":
    main()
