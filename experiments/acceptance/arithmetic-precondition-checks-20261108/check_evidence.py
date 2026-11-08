#!/usr/bin/env python3
"""Offline replay of the source restoration and fixed checked-recursion no-go evidence."""
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
import io
from pathlib import Path
import statistics
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
BASELINE="de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9"
CANDIDATE="905edec767a9e5eeee838e083cad93e027d73c51"
NATIVE_SOURCE="b31fbce898054f6db668277f8a4da88f94c95aa2"
FULL=(1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,
      191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096)
PATHS=("baseline","candidate","gmp")
OPS={0:"forced_full",1:"default_mul",2:"default_square"}
sha=lambda data:hashlib.sha256(data).hexdigest()


def main():
    manifest=json.loads((HERE/"manifest.json").read_text())
    evidence=HERE/"evidence.zip"
    with zipfile.ZipFile(evidence) as archive:
        actual=set(archive.namelist())
        expected={"objects/"+digest for digest in manifest["object_bytes"]}
        assert actual==expected,"evidence object inventory differs from manifest"
        def read(logical):
            digest=manifest["payload_sha256"][logical]
            data=archive.read("objects/"+digest)
            assert len(data)==manifest["object_bytes"][digest]
            assert sha(data)==digest,logical
            return data
        for digest,size in manifest["object_bytes"].items():
            data=archive.read("objects/"+digest)
            assert len(data)==size and sha(data)==digest,digest
        assert sha(evidence.read_bytes())==manifest["evidence_zip_sha256"]
        assert manifest["baseline_commit"]==BASELINE
        assert manifest["historical_candidate"]==CANDIDATE
        assert manifest["historical_native_source"]==NATIVE_SOURCE
        assert manifest["performance_accepted"] is False
        archived={row["prefix"]:(row["archive_sha256"],row["members"],row["payload_files"],row["bytes"])
                  for row in manifest["archives"]}
        assert archived["author-static"]==("260618cdf080c21067fcdfb788cb360d857c4f4c8766268ed6de84ab370cd8cd",1839,1839,30047009)
        assert archived["author-harness"]==("913ef075067c7966f1416eb6767913d2eded5f9731600653a78d40e2a1a93e37",10,10,15148)
        assert archived["independent-static"]==("d03ae3caca9534b4b8c226aa5f5784bbd4fb73b8aee6659d6e3a1629e08f14df",396,396,14797065)
        assert archived["independent-final/review-evidence.zip!"]==(
            "ec3acdc47d1da237e65ff3a6c83c81404d8b44e83997de4f1f45f22a41f38d45",104,104,3617934)

        restoration=json.loads(read("native-restoration.json"))
        assert restoration["base"]==BASELINE and restoration["historical_candidate"]==CANDIDATE
        assert restoration["sole_native_rust_delta_before_restoration"]==["native/verified/fast_multiply.rs"]
        assert restoration["native_all_files_identical_to_baseline"] is True
        assert sha(read("historical-candidate.patch"))==restoration["historical_patch_sha256"]
        native_hashes=restoration["native_sha256"]
        checkout=set(p.relative_to(ROOT).as_posix() for p in (ROOT/"native").rglob("*") if p.is_file())
        assert checkout==set(native_hashes),"checkout native inventory differs from the fixed baseline"
        for name,digest in native_hashes.items():
            data=(ROOT/name).read_bytes()
            assert sha(data)==digest,name

        historical=json.loads(read("author-static/check-4/verification.json"))
        producer=json.loads(read("author-static/semantic-3/build-source.json"))
        command=json.loads(read("author-static/semantic-3/build-command.json"))
        baseline=json.loads(read("author-static/baseline-binding/verification.json"))
        assert historical["status"]=="pass" and historical["benchmark_run"] is False
        assert historical["source"]["base"]==BASELINE
        assert historical["source"]["head"]=="162fdef515793ab72210102c8733c21f0110a23d"
        assert historical["producer"]["verified_items"]==359
        assert producer["head"]==NATIVE_SOURCE and command["returncode"]==0
        assert command["argv"][command["argv"].index("--no-cheating")+1]=="--compile"
        assert baseline["library_verified_items"]==358
        assert baseline["exports_sha256"]["libverigmp.rlib"]=="02dabb57ecbee4b82fe99b4ed555cbd892160b999b47d01d9ac0ab9788372d28"
        assert baseline["exports_sha256"]["verigmp.vir"]=="9890ff7d0d62f53101b41089017f913ecd6495421e54c79e2819735c3769ed41"
        assert sha(read("author-static/semantic-3/libverigmp.rlib"))=="1ce7a925da627ea99859935ec42ac88b5b3e67933bcf8a8e0c55b8827d685775"
        assert sha(read("author-static/semantic-3/verigmp.vir"))=="6054b60c6adad786bb95550364c61ffc725ac7abf965ddbe61f6d7f406749305"
        assert sha(read("author-static/semantic-3/source/native/verified/fast_multiply.rs"))=="7e8e225dd5edf54f384f3ea4d42aea03d59e3ab04d0050f3f04415b388219db8"
        baseline_rs={name:digest for name,digest in native_hashes.items() if name.endswith(".rs")}
        historical_rs=historical["source"]["native_sha256"]
        assert set(historical_rs)==set(baseline_rs)
        assert {name for name in baseline_rs if baseline_rs[name]!=historical_rs[name]}=={"native/verified/fast_multiply.rs"}
        for name,digest in historical_rs.items():
            assert sha(read("author-static/check-4/source/"+name))==digest
        producer_rs={name:digest for name,digest in producer["source_sha256"].items() if name.endswith(".rs")}
        assert producer_rs==historical_rs
        assert b"359 verified, 0 errors" in read("author-static/semantic-3/library.stdout.log")
        assert sha(read("author-static/baseline-binding/libverigmp.rlib"))==baseline["exports_sha256"]["libverigmp.rlib"]
        assert sha(read("author-static/baseline-binding/verigmp.vir"))==baseline["exports_sha256"]["verigmp.vir"]

        review=json.loads(read("independent-final/review.json"))
        assert review["verdict"]=="VALID NEGATIVE EVIDENCE / NO-GO PROMOTION"
        assert review["evidence_integrity_acceptance"] is True
        assert review["performance_acceptance"] is False and review["native_promotion_accepted"] is False
        assert review["baseline"]==BASELINE and review["reviewed_tip"]==CANDIDATE
        assert review["native_source"]==NATIVE_SOURCE
        assert manifest["final_review_sha256"]==sha(read("independent-final/review.json"))
        assert manifest["final_review_evidence_zip_sha256"]==archived["independent-final/review-evidence.zip!"][0]
        assert manifest["final_review_replay_check_sha256"]==sha(read("feature/independent-replay-check.json"))
        assert sha((HERE/"independent-review.json").read_bytes())==sha(read("feature/independent-review.json"))
        assert sha((HERE/"RESULTS.md").read_bytes())==sha(read("feature/RESULTS.md"))
        assert sha((HERE/"check_evidence.py").read_bytes())==sha(read("feature/check_evidence.py"))

        build=json.loads(read("author-static/bench-build/bench-build.json"))
        assert len(build["key_shapes"])==26
        cells=[(0,n,64) for n in FULL]+[(op,n,top) for op in (1,2) for n,top in build["key_shapes"]]
        assert len(cells)==86
        rows_by_run=[];run_results=[]
        for run_index in (1,2):
            prefix=f"measurement/run-{run_index}/"
            report=json.loads(read(prefix+"measurement.json"))
            raw_bytes=read(prefix+"raw.jsonl")
            raw_lines=raw_bytes.splitlines()
            assert report["status"]=="pass" and report["cpu"]==8
            assert report["seed"]==20261108 and report["repetitions"]==7
            assert report["minimum_sample_ns"]==10000000
            assert report["build_sha256"]==sha(read("author-static/bench-build/bench-build.json"))
            assert report["raw_sha256"]==sha(raw_bytes)
            assert report["run_id"]==f"precondition-cpu8-20261108-run-{run_index}"
            records=[json.loads(line) for line in raw_lines]
            assert len(records)==6192 and len(records)%3==0
            parsed=[]
            for offset in range(0,len(records),3):
                invocation,outcome,result=records[offset:offset+3]
                assert [x["record"] for x in (invocation,outcome,result)]==["invocation","outcome","result"]
                assert invocation["cpu"]==8 and invocation["timeout_seconds"]==180
                assert outcome["returncode"]==0 and outcome["timed_out"] is False
                for key in ("argv","op","n","top","path","kind","repetition"):
                    assert invocation[key]==outcome[key]==result[key]
                stdout=bytes.fromhex(outcome["stdout_hex"])
                stderr=bytes.fromhex(outcome["stderr_hex"])
                assert outcome["stdout"]==stdout.decode() and stderr==b"" and outcome["stderr"]==""
                decoded=json.loads(stdout)
                assert all(result[key]==value for key,value in decoded.items())
                argv=result["argv"];path=result["path"]
                binary=build["binaries"]["baseline" if path in ("baseline","gmp") else "candidate"]["path"]
                op,n,top=result["op"],result["n"],result["top"]
                assert argv[:6]==[binary,str(op),str(n),str(top),"20261108",str(path=="gmp").lower()]
                assert argv[7]=="registered"
                assert result["iterations"]>0 and result["ns"]>0
                if result["kind"]=="calibration":
                    assert argv[6]=="0" and result["ns"]>=20000000
                    ladder=result["calibration"]
                    assert ladder[-1]==[result["iterations"],result["ns"]]
                    assert [item[0] for item in ladder]==[1<<i for i in range(len(ladder))]
                else:
                    assert int(argv[6])==result["iterations"] and result["calibration"]==[]
                parsed.append(result)
            assert len(parsed)==2064
            cursor=0;cells_rows=[];retry_count=0
            for cell_index,(op,n,top) in enumerate(cells):
                measurements={path:[] for path in PATHS};checksums=set();counts={}
                def take(path,kind,repetition):
                    nonlocal cursor
                    row=parsed[cursor];cursor+=1
                    assert (row["op"],row["n"],row["top"],row["path"],row["kind"],row["repetition"])==(op,n,top,path,kind,repetition)
                    checksums.add(row["checksum"])
                    return row
                for path in PATHS:
                    calibration=take(path,"calibration",-1)
                    counts[path]=calibration["iterations"]
                for repetition in range(7):
                    pair=["baseline","candidate"] if repetition%2==0 else ["candidate","baseline"]
                    pair.insert((cell_index+repetition)%3,"gmp")
                    for path in pair:
                        sample=take(path,"sample",repetition)
                        assert sample["iterations"]==counts[path] and sample["ns"]>=10000000
                        measurements[path].append(Fraction(sample["ns"],sample["iterations"]))
                assert len(checksums)==1
                assert len({len(measurements[path]) for path in PATHS})==1
                medians={path:sorted(measurements[path])[3] for path in PATHS}
                saved=report["summaries"][cell_index]
                assert (saved["op"],saved["n"],saved["top"])==(op,n,top)
                floats={path:float(medians[path]) for path in PATHS}
                for path in PATHS:
                    assert math.isclose(saved["median_ns"][path],floats[path],rel_tol=1e-15)
                ratio=float(medians["candidate"]/medians["baseline"])
                gmp_ratio=float(medians["candidate"]/medians["gmp"])
                assert math.isclose(saved["candidate_over_baseline"],ratio,rel_tol=1e-15)
                assert math.isclose(saved["candidate_over_gmp"],gmp_ratio,rel_tol=1e-15)
                cells_rows.append(dict(run=run_index,operation=OPS[op],op=op,n=n,top=top,
                    baseline_ns=floats["baseline"],candidate_ns=floats["candidate"],gmp_ns=floats["gmp"],
                    candidate_over_baseline=ratio,candidate_over_gmp=gmp_ratio,samples_per_path=7,
                    regression_gt_105=ratio>1.05))
            assert cursor==len(parsed) and len(cells_rows)==86
            forced=[row["candidate_over_baseline"] for row in cells_rows if row["op"]==0 and row["n"]>24]
            assert len(forced)==27
            geomean=math.exp(sum(math.log(ratio) for ratio in forced)/len(forced))
            regressions=[row for row in cells_rows if row["candidate_over_baseline"]>1.05]
            slower=sum(row["candidate_over_baseline"]>1 for row in cells_rows)
            faster=sum(row["candidate_over_baseline"]<1 for row in cells_rows)
            maximum=max(cells_rows,key=lambda row:row["candidate_over_baseline"])
            assert math.isclose(geomean,review["runs"][run_index-1]["forced_recursive_geomean"],rel_tol=1e-12)
            assert math.isclose(maximum["candidate_over_baseline"],review["runs"][run_index-1]["maximum_candidate_over_baseline"],rel_tol=1e-15)
            assert len(regressions)==review["regression_counts_above_1_05"][run_index-1]
            assert slower==review["regression_counts_above_one"][run_index-1]
            run_pass=geomean<=0.97 and maximum["candidate_over_baseline"]<=1.05
            assert run_pass is False and review["runs"][run_index-1]["promotion_accepted"] is False
            rows_by_run.extend(cells_rows)
            run_results.append(dict(run=report["run_id"],completed=True,invocations=len(parsed),raw_records=len(records),
                calibration_calls=258,accepted_samples=1806,retries=retry_count,
                minimum_sample_ns=min(row["ns"] for row in parsed if row["kind"]=="sample"),
                forced_recursive_cells=27,forced_geomean=geomean,forced_geomean_pass=geomean<=0.97,
                all_cell_max_ratio=maximum["candidate_over_baseline"],all_cell_max=maximum,
                all_cell_limit_pass=maximum["candidate_over_baseline"]<=1.05,slower_cells=slower,
                faster_cells=faster,over_105=regressions,performance_no_go=True,
                gmp_principal_failures=sum(row["candidate_over_gmp"]>1 for row in cells_rows
                    if row["op"] in (1,2) and row["n"] in (256,512,1024,2048,4096) and row["top"]==63),
                gmp_key_over_12=sum(row["candidate_over_gmp"]>1.2 for row in cells_rows if row["op"] in (1,2))))
        original=json.loads(read("measurement/analysis.json"))
        assert original["performance_conclusion"]=="NO-GO under frozen promotion criteria"
        for index,result in enumerate(run_results):
            expected=original["runs"][index]
            assert math.isclose(expected["forced_recursive_geomean"],result["forced_geomean"],rel_tol=1e-12)
            assert expected["slower_than_baseline_count"]==result["slower_cells"]
            assert len(expected["regressions_gt_105"])==len(result["over_105"])
        ratio_csv=list(csv.DictReader(io.StringIO(read("measurement/all-86-ratios.csv").decode())))
        assert len(ratio_csv)==172 and len(rows_by_run)==172
        for expected_row,actual_row in zip(ratio_csv,rows_by_run):
            assert int(expected_row["run"])==actual_row["run"]
            assert int(expected_row["op"])==actual_row["op"]
            assert int(expected_row["n"])==actual_row["n"] and int(expected_row["top"])==actual_row["top"]
            assert math.isclose(float(expected_row["candidate_over_baseline"]),actual_row["candidate_over_baseline"],rel_tol=1e-15)
        assert sha((HERE/"native-restoration.json").read_bytes())==sha(read("feature/native-restoration.json"))
        assert sha((HERE/"independent-review.md").read_bytes())==sha(read("feature/independent-review.md"))
        assert sha((HERE/"independent-replay-check.json").read_bytes())==sha(read("feature/independent-replay-check.json"))
        csv_expected=list(csv.DictReader(io.StringIO(read("measurement/all-86-ratios.csv").decode())))
        assert len(csv_expected)==172
        for expected_row,actual_row in zip(csv_expected,rows_by_run):
            for key in ("run","op","n","top","samples_per_path"):
                assert int(expected_row[key])==actual_row[key]
            for key in ("baseline_ns","candidate_ns","gmp_ns","candidate_over_baseline","candidate_over_gmp"):
                assert math.isclose(float(expected_row[key]),actual_row[key],rel_tol=1e-15)

        host=json.loads(read("measurement/host-receipt.json"))
        assert host["status"]=="both_runs_completed_performance_not_decided"
        assert len(host["resume"])==2 and all(row["nt_status"]==0 for row in host["resume"])
        assert host["adb_before"]==host["adb_after"]
        phases={}
        for row in host["observations"]:phases.setdefault(row["phase"],{})[row["process"]["pid"]]=row["process"]
        assert len(host["paused"])==2
        for process in host["paused"]:
            pid=process["pid"];pause=phases["paused"][pid]
            assert pause["all_threads_suspended"] is True
            for phase in ("after-precondition-cpu8-20261108-run-1","after-precondition-cpu8-20261108-run-2"):
                sample=phases[phase][pid]
                assert sample["start_ticks"]==pause["start_ticks"] and sample["all_threads_suspended"] is True
                assert sample["cpu_seconds"]==pause["cpu_seconds"]
            resumed=phases["after-finally-resume"][pid]
            assert resumed["start_ticks"]==pause["start_ticks"] and resumed["all_threads_suspended"] is False
        assert sha(read("host-plan/timing_host.ps1"))=="8eabe0ee004dc3f58c1ac01dc6f9bceff770e2da944d4ae2ee2d47549241c9fb"
        assert sha(read("author-static/check-4/source/experiments/arithmetic-precondition-checks-20261108/PROTOCOL.md"))=="3c176e1b665aeae085c52094a68f6a6bfed5f1d77ed99deaa0ae55dc3d6e8d3e"
        assert sha(read("author-harness/harness-check-1/measure.py"))=="137d3b5607954f1fd3670220f73cd299d4f16bacb068a5a0981a30127137bcfa"

    rows_out=json.loads((HERE/"independent-review.json").read_text())
    assert rows_out["performance_acceptance"] is False and rows_out["native_promotion_accepted"] is False
    return dict(status="pass_no_go_evidence_verified",performance_accepted=False,production_native_matches_baseline=True,
        native_files=len(native_hashes),logical_payloads=len(manifest["payload_sha256"]),
        unique_payload_objects=len(manifest["object_bytes"]),runs=run_results,
        historical_candidate_359_items=True,production_baseline_358_items_reused_by_exact_identity=True,
        reviewer_verdict=rows_out["verdict"])


if __name__=="__main__":
    result=main()
    print(json.dumps(result,indent=2))
