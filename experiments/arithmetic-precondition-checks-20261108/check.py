#!/usr/bin/env python3
"""Focused static/semantic evidence; this command never runs timings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
FEATURE=Path(__file__).resolve().parent
BASE="de9ca4562c0c9c7d34f1a6a65cbaf48e48c7e1f9"
SOURCE="native/verified/fast_multiply.rs"
from oracle import generate
sys.path.insert(0,str(ROOT/"experiments/packed-convolution"))
from layout_verify import git_adapter,positive,file_sha
from verus_logs import strict_semantic_rejection,self_check


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps-root",required=True,type=Path)
    parser.add_argument("--producer",required=True,type=Path,help="fresh full modified-library build directory")
    parser.add_argument("--baseline",required=True,type=Path,help="accepted source-bound baseline producer")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args();out=args.output.resolve()
    if out.exists() or out.is_relative_to(ROOT):raise RuntimeError("use fresh external evidence")
    out.mkdir(parents=True)
    report=dict(status="running",benchmark_run=False,scope="checked full Karatsuba/private recursion",
                commands=[],mutants=[],codegen=[])
    def save(): (out/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
    def git(*argv):return subprocess.check_output(git_adapter()+list(argv),timeout=60)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
    def run(argv,name,cwd=out):
        result=subprocess.run(list(map(str,argv)),cwd=cwd,env=env,capture_output=True,timeout=900)
        for stream,data in (("stdout",result.stdout),("stderr",result.stderr)):
            (out/(name+"."+stream+".log")).write_bytes(data)
        text=(result.stdout+result.stderr).decode(errors="replace")
        report["commands"].append(dict(name=name,argv=list(map(str,argv)),cwd=str(cwd),
            returncode=result.returncode,stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),
            stderr_sha256=hashlib.sha256(result.stderr).hexdigest()))
        save();return result.returncode,text
    def ordinary(argv,name):
        code,text=run(argv,name)
        if code:raise RuntimeError("command failed: "+name)
        return text
    try:
        if git("status","--porcelain").strip():raise RuntimeError("commit candidate and test sources first")
        head=git("rev-parse","HEAD").decode().strip()
        names=[p.relative_to(ROOT).as_posix() for p in (ROOT/"native").rglob("*.rs")]
        names += [p.relative_to(ROOT).as_posix() for p in FEATURE.iterdir() if p.suffix in (".rs",".py",".md")]
        names += ["AGENTS.md","native/toolchain.json","native/performance-target.json","native/proof-status.json"]
        sources={name:(ROOT/name).read_bytes() for name in sorted(set(names))}
        for name,data in sources.items():
            if git("show",head+":"+name)!=data:raise RuntimeError("HEAD byte mismatch: "+name)
        native={name:hashlib.sha256(data).hexdigest() for name,data in sources.items()
                if name.startswith("native/") and name.endswith(".rs")}
        modified=[name for name,data in sources.items() if name in native and git("show",BASE+":"+name)!=data]
        if modified!=[SOURCE]:raise RuntimeError("changed kernel family exceeds registered scope")
        text=sources[SOURCE].decode()
        if re.search(r"\b(?:assume|admit|axiom)\s*\(|external_body|external_fn_specification|"
                     r"verifier::trusted|verify\s*=\s*false|\bunsafe\b|extern\s+\"C\"",text):
            raise RuntimeError("proof escape/unsafe/FFI in changed core")
        report["source"]=dict(head=head,base=BASE,native_sha256=native,
            all_inputs_sha256={name:hashlib.sha256(data).hexdigest() for name,data in sources.items()})
        report["strict_classifier_self_check"]=self_check()
        snapshot=out/"source"
        for name,data in sources.items():
            target=snapshot/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        deps=args.deps_root.resolve();pin=json.loads(sources["native/toolchain.json"])
        verifier=deps/"verus/verus-x86-linux/verus";rustup=deps/"cargo/bin/rustup"
        env.update(CARGO_HOME=str(deps/"cargo"),RUSTUP_HOME=str(deps/"rustup"),RUSTUP_TOOLCHAIN=pin["rust_toolchain"])
        env["PATH"]=str(deps/"cargo/bin")+os.pathsep+env.get("PATH","")
        archive=deps/"verus-download"/pin["archive"]
        if file_sha(archive)!=pin["sha256"]:raise RuntimeError("wrong pinned archive")
        tools={}
        with zipfile.ZipFile(archive) as bundle:
            for name in ("verus","rust_verify","z3","vstd.vir","libvstd.rlib","libverus_builtin.rlib",
                         "libverus_builtin_macros.so","libverus_state_machines_macros.so"):
                with bundle.open("verus-x86-linux/"+name) as stream:expected=hashlib.file_digest(stream,"sha256").hexdigest()
                if file_sha(verifier.parent/name)!=expected:raise RuntimeError("tool differs from pin: "+name)
                tools[name]=expected
        version=ordinary([verifier,"--version"],"verus-version")
        if pin["verus_version"] not in version or pin["rust_toolchain"] not in version:raise RuntimeError("wrong Verus version")
        rustc=[rustup,"run",pin["rust_toolchain"],"rustc"]
        rust_version=ordinary(rustc+["-vV"],"rustc-version")
        if "release: 1.99.1" not in rust_version:raise RuntimeError("wrong Rust version")
        sysroot=Path(ordinary(rustc+["--print","sysroot"],"rustc-sysroot").strip())
        for path in [rustup,sysroot/"bin/rustc",*list((sysroot/"lib").glob("*LLVM*.so*")),
                     *list((sysroot/"lib").glob("librustc_driver*.so"))]:tools[str(path)]=file_sha(path)
        report["tools"]=dict(archive_sha256=pin["sha256"],actual_sha256=tools,verus=version,rustc=rust_version)
        producer=args.producer.resolve();baseline=args.baseline.resolve()
        build=json.loads((producer/"build-source.json").read_text())
        if {k:v for k,v in build["source_sha256"].items() if k.endswith(".rs")}!=native:
            raise RuntimeError("modified producer is not this native source")
        proof=(producer/"library.stdout.log").read_text()+(producer/"library.stderr.log").read_text()
        verified=positive(0,proof)
        if verified!=359:raise RuntimeError("expected complete modified-library proof")
        old=json.loads((baseline/"verification.json").read_text())
        for name,expected in old["source_git"]["source_sha256"].items():
            if name.startswith("native/") and name.endswith(".rs"):
                if hashlib.sha256(git("show",BASE+":"+name)).hexdigest()!=expected:
                    raise RuntimeError("baseline producer source differs from committed base")
        for name,expected in old["exports_sha256"].items():
            if name in ("libverigmp.rlib","verigmp.vir") and file_sha(baseline/name)!=expected:
                raise RuntimeError("baseline export identity differs")
        for name in ("verus","rust_verify","z3","vstd.vir","libvstd.rlib"):
            expected=next(v for k,v in old["toolchain"]["actual_file_sha256"].items() if k.endswith("/"+name))
            if tools[name]!=expected:raise RuntimeError("baseline producer tool differs")
        report["producer"]=dict(build_source=build,verified_items=verified,
            rlib_sha256=file_sha(producer/"libverigmp.rlib"),vir_sha256=file_sha(producer/"verigmp.vir"))
        report["baseline"]=dict(source=BASE,report_sha256=file_sha(baseline/"verification.json"),
            rlib_sha256=file_sha(baseline/"libverigmp.rlib"),vir_sha256=file_sha(baseline/"verigmp.vir"),
            library_verified_items=old["library_verified_items"])
        for name in ("build-source.json","library.stdout.log","library.stderr.log","libverigmp.rlib","verigmp.vir"):
            shutil.copyfile(producer/name,out/name)
        ordinary(["c++","-std=c++17",snapshot/"native/controls/gmp_abi.cpp","-lgmp","-o",out/"gmp-abi"],"gmp-abi-build")
        report["gmp_abi"]=ordinary([out/"gmp-abi"],"gmp-abi-check")
        shapes=json.loads(sources["native/performance-target.json"])["key_shapes"]["shapes"]
        report["oracle"]=generate(out/"oracle",shapes)
        control=out/"libverigmp_control.rlib"
        flags=["-O","--edition=2024","-L",f"dependency={verifier.parent}"]
        ordinary(rustc+[snapshot/FEATURE.relative_to(ROOT)/"control.rs","--crate-name","verigmp_control",
            "--crate-type","lib",*flags,"-L",f"dependency={producer}","--extern",f"verigmp={producer/'libverigmp.rlib'}",
            "-o",control],"ordinary-control-build")
        report["runtime"]={}
        for label,library in (("baseline",baseline/"libverigmp.rlib"),("candidate",producer/"libverigmp.rlib"),
                              ("ordinary",producer/"libverigmp.rlib")):
            binary=out/(label+"-runtime")
            extra=["--cfg","ordinary_control","--extern",f"verigmp_control={control}"] if label=="ordinary" else []
            ordinary(rustc+[snapshot/FEATURE.relative_to(ROOT)/"runtime.rs",*flags,"-L",f"dependency={library.parent}",
                "--extern",f"verigmp={library}",*extra,"-o",binary],label+"-runtime-build")
            result=ordinary([binary,out/"oracle/cases.bin"],label+"-oracle")
            report["runtime"][label]=dict(status="pass",stdout=result,binary_sha256=file_sha(binary))
        report["ownership"]=[]
        fixtures={"alias":("E0502",'''fn main() {
    let mut words=[1u64;2];let b=[1u64];let mut scratch=[0u64;3];
    verigmp::fast_multiply::full(&mut words,&words[..1],&b,&mut scratch,24);
}'''),"private-worker":("E0603",'''fn main() {
    let _worker=verigmp::fast_multiply::full_inner;
}''')}
        for name,(diagnostic,source) in fixtures.items():
            path=out/(name+".rs");path.write_text(source+"\n")
            code,log=run(rustc+[path,*flags,"-L",f"dependency={producer}","--extern",
                f"verigmp={producer/'libverigmp.rlib'}","-o",out/name],name+"-negative")
            errors=re.findall(r"(?m)^error\[([^\]]+)\]:",log)
            if code!=1 or errors!=[diagnostic]:raise RuntimeError("wrong ownership/privacy rejection: "+name)
            report["ownership"].append(dict(fixture=name,diagnostic=diagnostic,status="pass"))
        mutant_specs=[("wrong-public-forwarding",lambda s:s.replace("full_inner(dst,a,b,scratch,threshold);",
            "full_inner(dst,a,a,scratch,threshold);",1)),
            ("weak-private-scratch",lambda s:s[:s.index("fn full_inner")]+s[s.index("fn full_inner"):].replace(
                "old(scratch)@.len()>=3*a@.len()","old(scratch)@.len()>=2*a@.len()",1)),
            ("wrong-child-partition",lambda s:s.replace("scratch.split_at_mut(2*k);","scratch.split_at_mut(2*k+1);",1))]
        for name,mutate in mutant_specs:
            folder=out/"mutants"/name;shutil.copytree(snapshot/"native",folder/"native")
            path=folder/SOURCE;changed=mutate(text)
            if changed==text:raise RuntimeError("missing mutation anchor")
            path.write_text(changed)
            code,log=run([verifier,folder/"native/lib.rs","--crate-type","lib","--crate-name","verigmp",
                "--verify-module","fast_multiply","--no-cheating","--multiple-errors","0","--num-threads","4"],"mutant-"+name,folder)
            rejected=strict_semantic_rejection(log,code,"fast_multiply")
            report["mutants"].append(dict(name=name,source_sha256=file_sha(path),strict_rejection=rejected))
            if not rejected:raise RuntimeError("not a complete logical mutant rejection: "+name)
        # Compile ordinary and actual complete objects; preserve entire symbol sections.
        objects={};bodies={}
        for label,library in (("baseline",baseline/"libverigmp.rlib"),("candidate",producer/"libverigmp.rlib"),("ordinary",control)):
            members=ordinary(["ar","t",library],label+"-archive-members").splitlines()
            member=next(name for name in members if name.endswith(".o"))
            obj=out/(label+".o");obj.write_bytes(subprocess.check_output(["ar","p",library,member]));objects[label]=obj
            table=ordinary(["objdump","-t","-C",obj],label+"-symbols")
            functions=["full","full_inner"] if label=="ordinary" else ["fast_multiply::full","fast_multiply::base_full",
                "fast_multiply::low","toom_multiply::full","square::full"]+(["fast_multiply::full_inner"] if label=="candidate" else [])
            prefix="verigmp_control::" if label=="ordinary" else "verigmp::"
            for function in functions:
                fields=next(line.split() for line in table.splitlines() if line.endswith(prefix+function))
                section=fields[3];size=int(fields[4],16);stem=label+"-"+function.replace("::","-")
                binary=out/(stem+".bin")
                ordinary(["objcopy","--dump-section",section+"="+str(binary),obj],stem+"-section")
                if binary.stat().st_size!=size:raise RuntimeError("incomplete symbol section")
                assembly=ordinary(["objdump","-d","-r","-C","--section="+section,obj],stem+"-assembly")
                bodies[(label,function)]=assembly
                if re.search(r"__rust_(?:alloc|realloc)|malloc|calloc|panic_bounds_check|Seq|radix::value",assembly):
                    raise RuntimeError("unexpected allocation/element-bounds/spec operation in inspected body")
                reloc=ordinary(["objdump","-r","-C","--section="+section,obj],stem+"-relocations")
                report["codegen"].append(dict(build=label,function=function,bytes=size,body_sha256=file_sha(binary),
                    complete_relocations=re.findall(r"(?m)^([0-9a-f]+)\s+(R_\S+)\s+(.+)$",reloc)))
        wrappers=[next(row for row in report["codegen"] if row["build"]==build and row["function"]==function)
                  for build,function in (("candidate","fast_multiply::full"),("ordinary","full"))]
        if wrappers[0]["body_sha256"]!=wrappers[1]["body_sha256"]:raise RuntimeError("public wrapper differs from plain control")
        def normalized(rows):
            return [(offset,kind,"private-worker" if "full_inner" in target else
                     "assert-data" if any(part in target for part in (".rodata",".data.rel.ro")) else target)
                    for offset,kind,target in rows]
        if normalized(wrappers[0]["complete_relocations"])!=normalized(wrappers[1]["complete_relocations"]):
            raise RuntimeError("public wrapper relocations differ from plain control")
        workers=[next(row for row in report["codegen"] if row["build"]==build and row["function"]==function)
                 for build,function in (("candidate","fast_multiply::full_inner"),("ordinary","full_inner"))]
        report["ordinary_comparison"]=dict(wrapper_bytes_equal=True,
            wrapper_normalized_relocations_equal=True,
            worker_bytes_equal=workers[0]["body_sha256"]==workers[1]["body_sha256"],
            actual_direct_add_cross_calls=bodies[("candidate","fast_multiply::full_inner")].count("fast_words::add_cross"),
            control_direct_add_cross_calls=bodies[("ordinary","full_inner")].count("fast_words::add_cross"),
            reason="different helper-inlining context: actual worker inlines cross accumulation; external ordinary control calls it",
            claim="full symbols and call graph inspected; no whole-worker byte-identity claim")
        for name,data in sources.items():
            if (ROOT/name).read_bytes()!=data:raise RuntimeError("source changed during gate")
        report["status"]="pass"
    except Exception as error:
        report["status"]="fail";report["failure"]=repr(error);raise
    finally:save()
    print(json.dumps(dict(status=report["status"],source=head,library_verified=verified,
        oracle_cases=report["oracle"]["cases"],mutants=len(report["mutants"]),
        report_sha256=file_sha(out/"verification.json")),indent=2))


if __name__=="__main__":main()
