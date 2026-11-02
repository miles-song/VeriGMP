"""Verified test-only callers derive ghost coefficients from separate inputs."""
from pathlib import Path
import json
S=Path(__file__).resolve().parent;root=S/'candidate/native'
plans=json.loads((S/'newton-operations.json').read_text())['plans']
parts=['//! Test-only verified callers; supplied coefficient inputs define the ghost witness.\nuse vstd::prelude::*;\nuse crate::{radix::*,toom8_newton,toom8_newton_spec as model};\nverus! {\n']
for plan in plans:
    d=plan['degree'];name='even' if d==5 else 'odd'
    params=','.join([f'a{i}:&mut[u64]' for i in range(d+1)]+[f'c{i}:&[u64]' for i in range(d+1)])
    pre=[f'old(a{i})@.len()==old(a0)@.len()' for i in range(1,d+1)]
    for i,weights in enumerate(plan['input_evaluations']):
        expr='+'.join(f'{w}int*value(c{j}@)' for j,w in enumerate(weights))
        pre.append(f'value(old(a{i})@)=={expr}')
    post=[f'final(a{i})@.len()==old(a{i})@.len()' for i in range(d+1)]+[f'value(final(a{i})@)==value(c{i}@)' for i in range(d+1)]
    parts.append(f'#[inline(always)]\npub fn {name}({params})\n    requires '+',\n        '.join(pre)+',\n    ensures '+',\n        '.join(post)+',\n{\n')
    parts.append('    let ghost c=seq!['+','.join(f'value(c{i}@)' for i in range(d+1))+(',0' if d==5 else '')+'];\n')
    parts.append('    proof {\n'+''.join(f'        prefix_range(c{i}@,c{i}@.len());\n' for i in range(d+1))+'        assert(model::nonnegative(c));\n    }\n')
    parts.append(f'    toom8_newton::{name}('+','.join(f'a{i}' for i in range(d+1))+',Ghost(c));\n}\n')
parts.append('}\n');(root/'toom8_newton_test_bridge.rs').write_text(''.join(parts))
imports='\n'.join(line for line in (root/'lib.rs').read_text().splitlines() if not line.startswith('//!'))+'\n#[path="toom8_newton_test_bridge.rs"] mod newton_test_bridge;\n'
runner='''fn main(){
    use std::io::{self,BufRead,Write};
    let mut output=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let args:Vec<u64>=line.split_whitespace().map(|s|s.parse().unwrap()).collect();
        assert!(args.len()>=2);let degree=args[0] as usize;assert!(degree==5 || degree==6);
        let n=usize::try_from(args[1]).unwrap();let count=(degree+1).checked_mul(n).unwrap();assert_eq!(args.len(),2usize.checked_add(count.checked_mul(2).unwrap()).unwrap());
        let mut buffers:[Vec<u64>;7]=std::array::from_fn(|_|vec![u64::MAX;n.checked_add(2).unwrap()]);
        for i in 0..degree+1 {buffers[i][1..n+1].copy_from_slice(&args[2+i*n..2+(i+1)*n]);}
        let coefficients=&args[2+count..];let saved=coefficients.to_vec();
        let c0=&coefficients[..n];let c1=&coefficients[n..2*n];let c2=&coefficients[2*n..3*n];let c3=&coefficients[3*n..4*n];let c4=&coefficients[4*n..5*n];let c5=&coefficients[5*n..6*n];
        let saved_extra=buffers[6].clone();let [a0,a1,a2,a3,a4,a5,a6]=&mut buffers;
        if degree==5 {newton_test_bridge::even(&mut a0[1..n+1],&mut a1[1..n+1],&mut a2[1..n+1],&mut a3[1..n+1],&mut a4[1..n+1],&mut a5[1..n+1],c0,c1,c2,c3,c4,c5);}
        else {let c6=&coefficients[6*n..];newton_test_bridge::odd(&mut a0[1..n+1],&mut a1[1..n+1],&mut a2[1..n+1],&mut a3[1..n+1],&mut a4[1..n+1],&mut a5[1..n+1],&mut a6[1..n+1],c0,c1,c2,c3,c4,c5,c6);}
        assert_eq!(coefficients,saved);if degree==5 {assert_eq!(buffers[6],saved_extra);}
        for (i,buf) in buffers[..degree+1].iter().enumerate(){
            assert_eq!((buf[0],buf[n+1]),(u64::MAX,u64::MAX));
            for (j,value) in buf[1..n+1].iter().enumerate(){if i*n+j>0{write!(output," ").unwrap();}write!(output,"{}",value).unwrap();}
        }
        writeln!(output).unwrap();
    }
}
'''
(root/'toom8_newton_runner.rs').write_text(imports+runner)
codegen=[]
for d,name in [(5,'even'),(6,'odd')]:
    params=','.join([f'a{i}:&mut[u64]' for i in range(d+1)]+[f'c{i}:&[u64]' for i in range(d+1)])
    args=','.join([f'a{i}' for i in range(d+1)]+[f'c{i}' for i in range(d+1)])
    codegen.append(f'#[no_mangle]pub fn verified_newton_{name}({params}){{newton_test_bridge::{name}({args});}}\n')
(root/'toom8_newton_codegen.rs').write_text(imports+''.join(codegen)+'fn main(){}\n')
