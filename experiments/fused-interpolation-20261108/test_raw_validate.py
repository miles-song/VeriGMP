#!/usr/bin/env python3
"""Synthetic adversarial raw-log checks; never executes a benchmark or verifier."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import tempfile

sys.dont_write_bytecode = True
from raw_validate import (CELLS, KEY_SHAPES, PAYLOAD, SEED, artifact, sha,
                          strict_json, validate_build, validate_report, validate_rows)

ROOT = Path(__file__).resolve().parents[2]


def fixture():
    spec = importlib.util.spec_from_file_location("original_measure",
        ROOT/"experiments/arithmetic-precondition-checks-20261108/measure.py")
    original = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(original)
    shapes = json.loads((ROOT/"native/performance-target.json").read_text())["key_shapes"]["shapes"]
    cells = [(0,n,64) for n in original.FULL_SIZES] + [(op,n,top) for op in (1,2) for n,top in shapes]
    assert cells == list(CELLS) and shapes == [list(pair) for pair in KEY_SHAPES]
    build = dict(binaries={name:dict(path="/synthetic/"+name+"-bench") for name in ("baseline","candidate")})
    rows = []
    summaries = []
    def emit(key,path,count,kind,rep,payload):
        op,n,top = key
        binary = build["binaries"]["baseline" if path in ("baseline","gmp") else "candidate"]["path"]
        argv = [binary,str(op),str(n),str(top),str(SEED),str(path=="gmp").lower(),str(count),"registered"]
        fields = dict(op=op,n=n,top=top,path=path,kind=kind,repetition=rep,argv=argv)
        stdout = (json.dumps(payload)+"\n").encode()
        rows.extend((dict(fields,record="invocation",cpu=8,timeout_seconds=180),
                     dict(fields,record="outcome",returncode=0,timed_out=False,stdout=stdout.decode(),
                          stderr="",stdout_hex=stdout.hex(),stderr_hex=""),
                     dict(fields,**payload,record="result")))
    for index,key in enumerate(cells):
        checksum = (index+1)*43
        counts = {name:4 for name in ("baseline","candidate","gmp")}
        groups = {name:[] for name in counts}
        for path in counts:
            emit(key,path,0,"calibration",-1,dict(iterations=4,ns=20_000_000,checksum=checksum,
                                                 calibration=[[1,1_000],[2,2_000],[4,20_000_000]]))
        for rep in range(7):
            for path in original.sample_paths(index,rep):
                count = counts[path]
                ns_per_iteration = 3_000_000 if path == "gmp" else 5_000_000
                ns = count*ns_per_iteration + rep*1_000
                kind = "sample"
                if (index,path,rep) == (0,"candidate",1):
                    emit(key,path,count,kind,rep,dict(iterations=count,ns=5_000_000,checksum=checksum,calibration=[]))
                    counts[path] *= 2
                    count = counts[path]
                    ns = count*ns_per_iteration + rep*1_000
                    kind = "sample-retry"
                emit(key,path,count,kind,rep,dict(iterations=count,ns=ns,checksum=checksum,calibration=[]))
                groups[path].append(ns/count)
        medians = {path:statistics.median(values) for path,values in groups.items()}
        summaries.append(dict(op=key[0],n=key[1],top=key[2],median_ns=medians,
            candidate_over_baseline=medians["candidate"]/medians["baseline"],
            candidate_over_gmp=medians["candidate"]/medians["gmp"]))
    return build,rows,summaries


def encoded(rows):
    return ("\n".join(json.dumps(row,sort_keys=True) for row in rows)+"\n").encode()


def self_check():
    build,rows,summaries = fixture()
    raw = encoded(rows)
    actual,receipt = validate_rows(raw,build,8)
    assert actual == summaries and receipt["calibrations"] == 258
    assert receipt["accepted_samples"] == 1806 and receipt["retained_retries"] == 1
    external_digest = sha(json.dumps(build).encode())
    report = dict(status="pass",seed=SEED,cpu=8,run_id="synthetic-only",build=build,
                  build_sha256=external_digest,minimum_sample_ns=10_000_000,repetitions=7,
                  raw_sha256=sha(raw),summaries=summaries)
    validate_report(report,raw,build,external_digest)
    failures = []
    def rejected(name,action):
        try:
            action()
        except (ValueError,KeyError,TypeError,UnicodeError):
            failures.append(name)
        else:
            raise AssertionError("validator accepted tampered fixture: "+name)
    def raw_case(name,change):
        altered = copy.deepcopy(rows)
        change(altered)
        rejected(name,lambda:validate_rows(encoded(altered),build,8))
    def report_case(name,change):
        altered = copy.deepcopy(report)
        change(altered)
        rejected(name,lambda:validate_report(altered,raw,build,external_digest))
    def payload_at(altered,offset,key,value):
        payload = strict_json(bytes.fromhex(altered[offset+1]["stdout_hex"]))
        payload[key] = value
        stdout = (json.dumps(payload)+"\n").encode()
        altered[offset+1].update(stdout=stdout.decode(),stdout_hex=stdout.hex())
        for name in PAYLOAD:
            altered[offset+2][name] = payload[name]
    def metadata_at(altered,offset,key,value):
        for row in altered[offset:offset+3]:
            row[key] = value
    retry = next(index for index in range(0,len(rows),3) if rows[index]["kind"] == "sample-retry")
    later_candidate = next(index for index in range(retry+3,len(rows),3)
                           if rows[index]["path"] == "candidate" and rows[index]["repetition"] == 2)
    raw_case("result-only-ns",lambda r:r[2].update(ns=1))
    raw_case("result-only-iterations",lambda r:r[2].update(iterations=8))
    raw_case("result-only-checksum",lambda r:r[2].update(checksum=0))
    raw_case("result-only-calibration",lambda r:r[2].update(calibration=[]))
    raw_case("stdout-text-hex-disagreement",lambda r:r[1].update(stdout="{}"))
    raw_case("stderr-text-hex-disagreement",lambda r:r[1].update(stderr_hex="ff"))
    raw_case("stdout-invalid-utf8",lambda r:r[1].update(stdout="\ufffd",stdout_hex="ff"))
    raw_case("failed-process",lambda r:r[1].update(returncode=1))
    raw_case("timed-out-process",lambda r:r[1].update(timed_out=True))
    raw_case("wrong-cpu",lambda r:r[0].update(cpu=7))
    raw_case("changed-timeout",lambda r:r[0].update(timeout_seconds=1))
    raw_case("unregistered-binary",lambda r:metadata_at(r,0,"argv",["/synthetic/other-bench",*r[0]["argv"][1:]]))
    raw_case("wrong-seed",lambda r:metadata_at(r,0,"argv",[*r[0]["argv"][:4],"20261109",*r[0]["argv"][5:]]))
    raw_case("wrong-gmp-selector",lambda r:metadata_at(r,0,"argv",[*r[0]["argv"][:5],"true",*r[0]["argv"][6:]]))
    raw_case("wrong-path-label",lambda r:metadata_at(r,0,"path","candidate"))
    raw_case("wrong-cell",lambda r:metadata_at(r,0,"n",2))
    raw_case("non-integer-metadata",lambda r:metadata_at(r,0,"op",False))
    raw_case("wrong-calibration-repetition",lambda r:metadata_at(r,0,"repetition",0))
    raw_case("calibration-count-not-zero",lambda r:metadata_at(r,0,"argv",[*r[0]["argv"][:6],"4","registered"]))
    raw_case("missing-calibration-ladder",lambda r:payload_at(r,0,"calibration",[]))
    raw_case("non-doubling-calibration",lambda r:payload_at(r,0,"calibration",[[1,1_000],[3,2_000],[4,20_000_000]]))
    raw_case("calibration-starts-at-two",lambda r:payload_at(r,0,"calibration",[[2,2_000],[4,20_000_000]]))
    raw_case("calibration-continues-after-threshold",lambda r:payload_at(r,0,"calibration",[[1,20_000_000],[2,2_000],[4,20_000_000]]))
    raw_case("calibration-terminal-disagrees",lambda r:payload_at(r,0,"ns",20_000_001))
    raw_case("calibration-stops-too-soon",lambda r:payload_at(r,0,"calibration",[[1,1_000],[2,2_000],[4,19_000_000]]))
    raw_case("calibration-checksum-disagrees",lambda r:payload_at(r,0,"checksum",0))
    raw_case("boolean-ns",lambda r:payload_at(r,0,"ns",True))
    raw_case("negative-checksum",lambda r:payload_at(r,0,"checksum",-1))
    raw_case("overflow-checksum",lambda r:payload_at(r,0,"checksum",1<<64))
    raw_case("calibration-order",lambda r:r.__setitem__(slice(0,6),r[3:6]+r[0:3]))
    raw_case("sample-order",lambda r:r.__setitem__(slice(9,15),r[12:15]+r[9:12]))
    raw_case("missing-triple",lambda r:r.__delitem__(slice(9,12)))
    raw_case("extra-triple",lambda r:r.extend(copy.deepcopy(r[-3:])))
    raw_case("missing-final-cell",lambda r:r.__delitem__(slice(-72,None)))
    raw_case("sample-calibration-nonempty",lambda r:payload_at(r,9,"calibration",[[1,20_000_000]]))
    raw_case("sample-count-disagrees-with-argv",lambda r:payload_at(r,9,"iterations",8))
    raw_case("retry-not-doubling",lambda r:metadata_at(r,retry,"argv",[*r[retry]["argv"][:6],"12","registered"]))
    raw_case("retry-wrong-kind",lambda r:metadata_at(r,retry,"kind","sample"))
    raw_case("retry-wrong-path",lambda r:metadata_at(r,retry,"path","baseline"))
    raw_case("retry-checksum-disagrees",lambda r:payload_at(r,retry,"checksum",0))
    raw_case("short-sample-retry-removed",lambda r:r.__delitem__(slice(retry,retry+3)))
    raw_case("retry-after-accepted-sample",lambda r:metadata_at(r,9,"kind","sample-retry"))
    raw_case("retry-count-not-persisted",lambda r:metadata_at(r,later_candidate,"argv",[*r[later_candidate]["argv"][:6],"4","registered"]))
    report_case("report-raw-digest",lambda r:r.update(raw_sha256="0"*64))
    report_case("report-embedded-build",lambda r:r["build"]["binaries"]["candidate"].update(path="/synthetic/other"))
    report_case("report-external-build-digest",lambda r:r.update(build_sha256="0"*64))
    report_case("report-median",lambda r:r["summaries"][0]["median_ns"].update(candidate=1.0))
    report_case("report-candidate-baseline-ratio",lambda r:r["summaries"][0].update(candidate_over_baseline=0.5))
    report_case("report-candidate-gmp-ratio",lambda r:r["summaries"][0].update(candidate_over_gmp=0.5))
    report_case("report-summary-order",lambda r:r["summaries"].reverse())
    report_case("report-repetitions",lambda r:r.update(repetitions=6))
    report_case("report-status",lambda r:r.update(status="fail"))
    rejected("external-build-anchor",lambda:validate_build(b"{}","0"*64))
    rejected("duplicate-json-key",lambda:strict_json('{"ns":1,"ns":2}'))
    rejected("non-finite-json",lambda:strict_json('{"ns":NaN}'))
    with tempfile.TemporaryDirectory(prefix="fused-validator-synthetic-") as temporary:
        path = Path(temporary)/"artifact"
        path.write_bytes(b"synthetic artifact, never executable")
        reference = dict(path=path.as_posix(),sha256=sha(path.read_bytes()))
        if path.as_posix().startswith("/"):
            assert artifact(reference) == path.read_bytes()
            path.write_bytes(b"changed synthetic artifact")
            rejected("artifact-content-drift",lambda:artifact(reference))
    return dict(status="pass",synthetic_only=True,benchmark_executed=False,verifier_executed=False,
                original_schedule_cells=86,original_sample_order_cases=602,
                positive_raw_validation=receipt,synthetic_raw_sha256=sha(raw),
                rejected_tamper_cases=len(failures),rejected_tampers=failures)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("use a fresh synthetic verification output")
    result = self_check()
    result["source_sha256"] = {path.name:sha(path.read_bytes()) for path in
        (Path(__file__),Path(__file__).with_name("raw_validate.py"),Path(__file__).with_name("summarize.py"))}
    result["python"] = sys.version
    result["python_sha256"] = sha(Path(sys.executable).read_bytes())
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(status=result["status"],rejected_tamper_cases=result["rejected_tamper_cases"],
                         benchmark_executed=False,report_sha256=sha(args.output.read_bytes())),indent=2))


if __name__ == "__main__":
    main()
