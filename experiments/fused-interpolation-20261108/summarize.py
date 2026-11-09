#!/usr/bin/env python3
"""Adjudicate two complete frozen runs. Never runs or retries a measurement."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from raw_validate import CELLS, require, strict_json, validate_build, validate_report

PRIMARY = {(1,n,63) for n in (512,513,1023,1024,1025,2048,4096)}
PRIMARY |= {(2,n,63) for n in (511,512,513,1023,1024,1025,2048,4096)}


def geomean(values):
    require(values and all(x > 0 and math.isfinite(x) for x in values),"invalid geometric mean input")
    return math.exp(sum(map(math.log,values))/len(values))


def cell(row):
    return row["op"],row["n"],row["top"]


def adjudicate(rows,expected):
    require(len(rows) == 86 and {cell(row) for row in rows} == expected,"incomplete adjudication matrix")
    ratios = {}
    for row in rows:
        values = row["median_ns"]
        require(set(values) == {"baseline","candidate","gmp"},"wrong median paths")
        require(all(x > 0 and math.isfinite(x) for x in values.values()),"invalid medians")
        ratio = values["candidate"]/values["baseline"]
        require(math.isclose(ratio,row["candidate_over_baseline"],rel_tol=1e-14),"ratio differs from medians")
        ratios[cell(row)] = ratio
    primary = geomean([ratios[key] for key in sorted(PRIMARY)])
    worst = max(ratios.values())
    return dict(primary_geomean=primary,all_86_worst=worst,
                primary_pass=primary<=0.98,all_86_pass=worst<=1.05,
                performance_pass=primary<=0.98 and worst<=1.05,
                failed_cells=[dict(cell=key,ratio=value) for key,value in sorted(ratios.items()) if value>1.05])


def load_run(folder,build,build_sha256):
    folder = Path(folder).resolve()
    report = strict_json((folder/"measurement.json").read_bytes())
    raw = (folder/"raw.jsonl").read_bytes()
    recomputed,raw_validation = validate_report(report,raw,build,build_sha256)
    expected = set(CELLS)
    summaries = {cell(row):row for row in recomputed}
    result = adjudicate(recomputed,expected)
    result.update(run_id=report["run_id"],raw_sha256=report["raw_sha256"],
                  measurement_sha256=hashlib.sha256((folder/"measurement.json").read_bytes()).hexdigest(),
                  raw_validation=raw_validation)
    return report,summaries,result,expected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run1",required=True,type=Path)
    p.add_argument("--run2",required=True,type=Path)
    p.add_argument("--build",required=True,type=Path,help="externally frozen bench-build.json")
    p.add_argument("--build-sha256",required=True,help="digest from root/independent pre-timing receipt")
    p.add_argument("--output",required=True,type=Path)
    args = p.parse_args()
    require(args.run1.resolve() != args.run2.resolve() and not args.output.exists(),"use distinct runs and a fresh report")
    build,identity = validate_build(args.build.read_bytes(),args.build_sha256)
    a,rows1,result1,expected = load_run(args.run1,build,args.build_sha256)
    b,rows2,result2,expected2 = load_run(args.run2,build,args.build_sha256)
    require(expected == expected2 and a["run_id"] != b["run_id"],"runs are not independent identities")
    require(a["build_sha256"] == b["build_sha256"] and a["build"] == b["build"],"frozen build differs between runs")
    require(a["cpu"] == b["cpu"] == 8,"CPU changed")
    controls = expected-PRIMARY
    baseline = {key:rows2[key]["median_ns"]["baseline"]/rows1[key]["median_ns"]["baseline"] for key in controls}
    mean = geomean(list(baseline.values()))
    drift = not 0.95<=mean<=1.05 or any(not 0.90<=value<=1.10 for value in baseline.values())
    report = dict(status="adjudicated",new_measurements_executed=False,performance_thresholds=dict(primary_geomean_max=0.98,all_86_worst_max=1.05),
        runs=[result1,result2],same_frozen_build=True,cpu=8,seed=20261108,
        build_sha256=args.build_sha256,identity_receipt=build["identity_receipt"],
        source_identity={key:{name:value for name,value in source.items() if name not in ("root","files")}
                         for key,source in identity["sources"].items()},
        baseline_validation=dict(control_cells=71,run2_over_run1_geomean=mean,baseline_drift=drift,
            all_control_ratios=[dict(cell=key,run2_over_run1=value) for key,value in sorted(baseline.items())]),
        numeric_gates_pass=result1["performance_pass"] and result2["performance_pass"] and not drift,
        promotion_requires="root-approved protocol, frozen host/control identities, all static gates and independent review in addition to numeric gates",
        gmp_parity=False)
    args.output.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
