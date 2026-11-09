"""Prepare isolated strict semantic mutants; never invokes a verifier or timing."""
import hashlib
import json
from pathlib import Path
import shutil

MUTATIONS = (
    ("wrong-shift","toom_interpolate","verified/toom_interpolate.rs",
     "sub_shifted_exact(p2,z4,4)","sub_shifted_exact(p2,z4,1)"),
    ("lost-shift-carry","toom_words","verified/toom_words.rs",
     "carry=next_carry;borrow=next_borrow;i+=1;","carry=0;borrow=next_borrow;i+=1;"),
    ("lost-borrow","toom_words","verified/toom_words.rs",
     "carry=next_carry;borrow=next_borrow;i+=1;","carry=next_carry;borrow=0;i+=1;"),
    ("zero-scalar-shift-carry","toom_words","verified/toom_words.rs",
     "let low=(word<<shift)|carry;let high=word>>(64-shift);",
     "let low=(word<<shift)|carry;let high=0u64;"),
)


def check_anchors(native):
    checked = []
    for name,module,source,before,after in MUTATIONS:
        data = (Path(native)/source).read_text()
        assert data.count(before) == 1, name
        assert before != after
        checked.append(dict(name=name,module=module,source="native/"+source))
    return checked


def prepare(native,output):
    native = Path(native).resolve()
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(native):
        raise RuntimeError("use a fresh directory outside the source")
    check_anchors(native)
    output.mkdir(parents=True)
    rows = []
    for name,module,source,before,after in MUTATIONS:
        folder = output/name
        shutil.copytree(native,folder/"native")
        path = folder/"native"/source
        path.write_text(path.read_text().replace(before,after,1),encoding="utf-8",newline="\n")
        rows.append(dict(name=name,module=module,source=str(path),
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            verifier_arguments=["native/lib.rs","--crate-name","verigmp","--crate-type","lib",
                "--verify-module",module,"--no-cheating","--multiple-errors","0","--num-threads","2"],
            required_classification="strict_semantic_rejection(log,returncode,module) is True"))
    (output/"mutants.json").write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
    return rows
