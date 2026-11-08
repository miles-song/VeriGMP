#!/usr/bin/env python3
"""Controlled harness fixtures only; never execute a benchmark or verifier."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.dont_write_bytecode=True
import measure

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"experiments/packed-convolution"))
from layout_verify import git_adapter


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args();ev=args.evidence.resolve();out=args.output.resolve();out.mkdir()
    report=dict(status="running",benchmark_executed=False,verifier_executed=False,
                order_cases=[],process_cases=[])
    def save():(out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    save()
    try:
        old=json.loads((ev/"check-4/verification.json").read_text())
        for name,expected in old["source"]["native_sha256"].items():
            assert sha(ROOT/name)==expected,name
        assert sha(ROOT/"experiments/arithmetic-precondition-checks-20261108/bench.rs")==old["source"]["all_inputs_sha256"]["experiments/arithmetic-precondition-checks-20261108/bench.rs"]
        build=json.loads((ev/"bench-build/bench-build.json").read_text())
        for row in build["binaries"].values():assert sha(Path(row["path"]))==row["sha256"]
        report["reuse"]=dict(native_fixed_source="b31fbce898054f6db668277f8a4da88f94c95aa2",
            native_sha256=old["source"]["native_sha256"],benchmark_binaries=build["binaries"],
            prior_report_sha256=sha(ev/"check-4/verification.json"),
            prior_archive_sha256=sha(ev/"prereview-raw.zip"))
        feature=Path(__file__).resolve().parent
        report["source"]=dict(head=subprocess.check_output(git_adapter()+["rev-parse","HEAD"]).decode().strip(),
            sha256={path.name:sha(path) for path in (feature/"measure.py",Path(__file__))},
            python_executable=str(Path(sys.executable).resolve()),python_sha256=sha(Path(sys.executable)))
        for path in (feature/"measure.py",Path(__file__)):(out/path.name).write_bytes(path.read_bytes())
        cells=[(0,n,64) for n in measure.FULL_SIZES]+[(op,n,top) for op in (1,2) for n,top in build["key_shapes"]]
        assert len(cells)==86
        for index,cell in enumerate(cells):
            for rep in range(7):
                order=measure.sample_paths(index,rep)
                assert sorted(order)==["baseline","candidate","gmp"]
                assert (order.index("baseline")<order.index("candidate"))==(rep%2==0)
                assert order.index("gmp")==((index+rep)%3)
                report["order_cases"].append(dict(cell=list(cell),repetition=rep,order=order))
        stub=out/"stub.py"
        stub.write_text('''import json,sys,threading
mode=sys.argv[1]
sys.stdout.buffer.write(("stdout:"+mode+"\\n").encode() if mode!="valid" else b"")
sys.stdout.buffer.flush()
sys.stderr.buffer.write(("stderr:"+mode+"\\n").encode()+b"\\xff")
sys.stderr.buffer.flush()
if mode=="nonzero":sys.exit(7)
if mode=="timeout":threading.Event().wait(60)
if mode=="valid":print(json.dumps(dict(iterations=4,ns=20000000,checksum=42,calibration=[])))
''')
        parse=json.loads
        for mode,expected_error in (("valid",None),("nonzero",RuntimeError),("timeout",TimeoutError),
                                    ("invalid-json",json.JSONDecodeError)):
            log=out/(mode+".jsonl");command=[sys.executable,str(stub),mode]
            fields=dict(op=0,n=25,top=64,path="candidate",kind="controlled-fixture",repetition=0)
            parsed=[];caught=None
            def probe(data):
                rows=[parse(line) for line in log.read_text().splitlines()]
                assert [row["record"] for row in rows]==["invocation","outcome"]
                assert sync.call_count==2
                parsed.append(True);return parse(data)
            with log.open("w") as raw,patch.object(measure.os,"fsync",wraps=os.fsync) as sync,patch.object(measure.json,"loads",side_effect=probe):
                try:row=measure.invoke(command,raw,fields,None,timeout=2)
                except Exception as error:caught=error
            if expected_error is None:
                assert caught is None,repr(caught)
                assert row["iterations"]==4 and row["ns"]==20000000 and row["checksum"]==42
            else:assert type(caught) is expected_error,repr(caught)
            rows=[parse(line) for line in log.read_text().splitlines()]
            assert rows[0]["record"]=="invocation" and rows[0]["argv"]==command
            outcome=rows[1];assert outcome["record"]=="outcome"
            for key,value in fields.items():assert outcome[key]==value
            assert bytes.fromhex(outcome["stderr_hex"])==("stderr:"+mode+"\n").encode()+b"\xff"
            if mode!="valid":assert bytes.fromhex(outcome["stdout_hex"])==("stdout:"+mode+"\n").encode()
            assert outcome["returncode"]==({"nonzero":7,"timeout":-9}.get(mode,0))
            assert outcome["timed_out"]==(mode=="timeout")
            assert len(parsed)==(1 if mode in ("valid","invalid-json") else 0)
            assert [r["record"] for r in rows]==["invocation","outcome"]+(
                ["result"] if mode=="valid" else ["parse_failure"] if mode=="invalid-json" else [])
            assert sync.call_count==len(rows)
            report["process_cases"].append(dict(mode=mode,status="pass",raw_sha256=sha(log),
                records=len(rows),exception=type(caught).__name__ if caught else None,
                retained_before_parse=bool(parsed),fsync_calls=sync.call_count))
        report["status"]="pass"
    except Exception as error:report["status"]="fail";report["failure"]=repr(error);raise
    finally:save()
    print(json.dumps(dict(status=report["status"],order_cases=len(report["order_cases"]),
        process_cases=len(report["process_cases"]),benchmark_executed=False,
        report_sha256=sha(out/"verification.json")),indent=2))


if __name__=="__main__":main()
