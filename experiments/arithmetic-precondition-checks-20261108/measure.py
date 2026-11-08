#!/usr/bin/env python3
"""Run only after root grants the quiet window; preserve every raw duration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess

FULL_SIZES=(1,2,7,8,9,23,24,25,31,32,33,47,48,49,63,64,65,127,128,129,
            191,192,193,255,256,257,511,512,513,1023,1024,1025,2048,4096)
SEED=20261108


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build",required=True,type=Path,help="frozen bench-build.json")
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--run-id",required=True)
    parser.add_argument("--cpu",type=int,default=0)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(exist_ok=False)
    build=json.loads(args.build.read_text())
    files={label:Path(row["path"]) for label,row in build["binaries"].items()}
    for label,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=build["binaries"][label]["sha256"]:
            raise RuntimeError("release binary changed")
    shapes=build["key_shapes"]
    cells=[(0,n,64) for n in FULL_SIZES]+[(op,n,top) for op in (1,2) for n,top in shapes]
    report=dict(status="running",run_id=args.run_id,seed=SEED,cpu=args.cpu,
                build_sha256=hashlib.sha256(args.build.read_bytes()).hexdigest(),build=build,
                minimum_sample_ns=10_000_000,repetitions=7,summaries=[])
    raw=(out/"raw.jsonl").open("w")
    def call(cell,path,count,kind,rep):
        op,n,top=cell;binary=files["baseline" if path in ("baseline","gmp") else "candidate"]
        command=[str(binary),str(op),str(n),str(top),str(SEED),str(path=="gmp").lower(),str(count),"registered"]
        result=subprocess.run(command,capture_output=True,text=True,check=True,timeout=180,
                              preexec_fn=lambda:os.sched_setaffinity(0,{args.cpu}))
        row=json.loads(result.stdout)
        row.update(op=op,n=n,top=top,path=path,kind=kind,repetition=rep,argv=command)
        raw.write(json.dumps(row,sort_keys=True)+"\n");raw.flush();return row
    try:
        for index,cell in enumerate(cells):
            counts={};groups={path:[] for path in ("baseline","candidate","gmp")}
            checksums=set()
            for path in groups:
                row=call(cell,path,0,"calibration",-1);counts[path]=row["iterations"];checksums.add(row["checksum"])
            for rep in range(7):
                paths=["baseline","candidate","gmp"] if rep%2==0 else ["candidate","baseline","gmp"]
                offset=(index+rep)%3;paths=paths[offset:]+paths[:offset]
                for path in paths:
                    row=call(cell,path,counts[path],"sample",rep);checksums.add(row["checksum"])
                    while row["ns"]<10_000_000:
                        counts[path]*=2;row=call(cell,path,counts[path],"sample-retry",rep)
                        checksums.add(row["checksum"])
                    groups[path].append(row["ns"]/row["iterations"])
            if len(checksums)!=1:raise RuntimeError("before/after/GMP result mismatch")
            medians={path:statistics.median(values) for path,values in groups.items()}
            report["summaries"].append(dict(op=cell[0],n=cell[1],top=cell[2],median_ns=medians,
                candidate_over_baseline=medians["candidate"]/medians["baseline"],
                candidate_over_gmp=medians["candidate"]/medians["gmp"]))
            (out/"measurement.json").write_text(json.dumps(report,indent=2)+"\n")
        report["status"]="pass"
        for label,path in files.items():
            if hashlib.sha256(path.read_bytes()).hexdigest()!=build["binaries"][label]["sha256"]:
                raise RuntimeError("release binary changed during run")
    except Exception as error:
        report["status"]="fail";report["failure"]=repr(error);raise
    finally:
        raw.close();report["raw_sha256"]=hashlib.sha256((out/"raw.jsonl").read_bytes()).hexdigest()
        (out/"measurement.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(status=report["status"],cells=len(cells),run=args.run_id,
        report_sha256=hashlib.sha256((out/"measurement.json").read_bytes()).hexdigest()),indent=2))


if __name__=="__main__":main()
