from pathlib import Path
import hashlib,json,re
S=Path(__file__).resolve().parent;P=S.parent/'toom8-pair-stage-e22a4dd'
imports=(S/'candidate/native/lib.rs').read_text()
wrappers='''
#[no_mangle] pub fn verified_producer_generic(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,w:[u64;8],s:&mut[u64]){toom8_producer::weighted_pair(e,o,a,b,k,w,s,24);}
#[no_mangle] pub fn verified_producer_point_one(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_producer::weighted_pair(e,o,a,b,k,[1;8],s,24);}
#[no_mangle] pub fn verified_producer_point_eight(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_producer::weighted_pair(e,o,a,b,k,[1,8,64,512,4096,32768,262144,2097152],s,24);}
fn main(){}
'''
(S/'candidate/native/toom8_producer_codegen.rs').write_text(imports+wrappers)
inspector=(P/'pair_codegen.py').read_text().replace("['verified_pair_generic','verified_pair_positive','verified_pair_negative','verified_pair_half']","['verified_producer_generic','verified_producer_point_one','verified_producer_point_eight']")
inspector=inspector.replace("if 'core' in target and 'panicking' in target:external.add(target);continue", "if target in ('*memcpy@GOTPCREL(%rip)','*memset@GOTPCREL(%rip)') or ('core' in target and ('panicking' in target or 'slice_index_fail' in target)):external.add(target);continue")
inspector=inspector.replace('Actual simultaneous signed sum/difference and exact parity-normalization caller','Actual eight-block evaluation/product/pair composition and child multiplication paths')
(S/'producer_codegen.py').write_text(inspector)
mutants=[
 ('wrong-positive-a','a0,a1,a2,a3,a4,a5,a6,a7,weights,false);','a0,a1,a2,a3,a4,a5,a6,a7,weights,true);'),
 ('wrong-positive-b','b0,b1,b2,b3,b4,b5,b6,b7,weights,false);','b0,b1,b2,b3,b4,b5,b6,b7,weights,true);'),
 ('wrong-positive-product','toom4_multiply::full(even,ax,bx,work,threshold);','toom4_multiply::full(even,ax,ax,work,threshold);'),
 ('wrong-negative-product','toom4_multiply::full(odd,ax,bx,work,threshold);','toom4_multiply::full(odd,ax,ax,work,threshold);'),
 ('ignore-product-sign','let negative=na!=nb;','let negative=false;'),
 ('skip-pair-halving','toom8_pair::half_pair(plus,minus,negative);','toom8_pair::sum_difference(plus,minus,negative);'),
 ('drop-input-block','let a7=&a[7*k..];','let a7=&a[a.len()..];'),
 ('zero-weights','let m=k+1;','let m=k+1;let weights=[0u64;8];')]
code=(P/'check_pair.py').read_text().replace('pair_oracle','producer_oracle').replace('pair_codegen','producer_codegen').replace('check_pair.py','check_producer.py')
start=code.index('MUTANTS=');end=code.index('\ntag=sys.argv[1]',start);code=code[:start]+'MUTANTS='+repr(mutants)+code[end:]
code=code.replace('native/verified/toom8_pair.rs','native/verified/toom8_producer.rs').replace('toom8_pair_runner.rs','toom8_producer_runner.rs').replace('toom8_pair_codegen.rs','toom8_producer_codegen.rs').replace('toom8_pair','toom8_producer').replace('pair_candidate','producer_candidate')
# The execution intentionally retains its call to the already-verified pair API.
start=code.index('MUTANTS=');end=code.index('\ntag=sys.argv[1]',start);code=code[:start]+'MUTANTS='+repr(mutants)+code[end:]
code=code.replace("'origin.json']]","'origin.json','scope.json','generate_convolution_spec.py','prepare_runner.py','prepare_gate.py']]")
code=code.replace('Actual simultaneous signed sum/difference and exact parity normalization; not a completed Toom8 kernel','Actual eight-block evaluation and multiplication establish signed pair preconditions; not a completed Toom8 kernel')
code=code.replace('Independent Python unbounded signed sum/difference and exact halving','Independent Python double sum of sixty-four weighted input-block products')
(S/'check_producer.py').write_text(code)
origin=json.loads((S/'origin.json').read_text())
origin['inherited_native_sha256']={n:h for n,h in origin['parent_native_sha256'].items() if n!='candidate/native/lib.rs'}
(S/'origin.json').write_text(json.dumps(origin,indent=2)+'\n')
