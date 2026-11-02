from pathlib import Path
import hashlib,json
S=Path(__file__).resolve().parent;P=S.parent/'toom8-producer-stage-e22a4dd'
imports=(S/'candidate/native/lib.rs').read_text()
runner=r'''
fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),8);assert_eq!(f[0],"dyadic");
        let k:usize=f[1].parse().unwrap();let threshold:usize=f[2].parse().unwrap();assert!(threshold>=24);
        let exponent:u32=f[3].parse().unwrap();assert!(exponent<=3);let reciprocal:u32=f[4].parse().unwrap();assert!(reciprocal<=1);
        let a=words(f[5]);let b=words(f[6]);assert_eq!(a.len(),b.len());assert!(a.len()>=k.checked_mul(7).unwrap() && a.len()<=k.checked_mul(8).unwrap());
        let extra:usize=f[7].parse().unwrap();assert!(extra<=64);let m=k.checked_add(1).unwrap();let n=m.checked_mul(2).unwrap();let work_len=m.checked_mul(14).unwrap().checked_add(extra).unwrap();
        let before_a=a.clone();let before_b=b.clone();let mut even=vec![u64::MAX;n+2];let mut odd=vec![0x55aa55aa55aa55aa;n+2];let mut work=vec![0x1122334455667788;work_len+2];
        toom8_dyadic_producer::dyadic_pair(&mut even[1..n+1],&mut odd[1..n+1],&a,&b,k,exponent,reciprocal!=0,&mut work[1..work_len+1],threshold);
        assert_eq!(a,before_a);assert_eq!(b,before_b);assert_eq!((even[0],even[n+1]),(u64::MAX,u64::MAX));assert_eq!((odd[0],odd[n+1]),(0x55aa55aa55aa55aa,0x55aa55aa55aa55aa));assert_eq!((work[0],work[work_len+1]),(0x1122334455667788,0x1122334455667788));
        writeln!(out,"{}",even[1..n+1].iter().chain(odd[1..n+1].iter()).map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
'''
(S/'candidate/native/toom8_dyadic_producer_runner.rs').write_text(imports+runner)
wrappers='''
#[no_mangle] pub fn verified_dyadic_generic(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,x:u32,r:bool,s:&mut[u64]){toom8_dyadic_producer::dyadic_pair(e,o,a,b,k,x,r,s,24);}
#[no_mangle] pub fn verified_dyadic_eight(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_dyadic_producer::dyadic_pair(e,o,a,b,k,3,false,s,24);}
#[no_mangle] pub fn verified_dyadic_reciprocal_eight(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_dyadic_producer::dyadic_pair(e,o,a,b,k,3,true,s,24);}
fn main(){}
'''
(S/'candidate/native/toom8_dyadic_producer_codegen.rs').write_text(imports+wrappers)
inspector=(P/'producer_codegen.py').read_text().replace("['verified_producer_generic','verified_producer_point_one','verified_producer_point_eight']","['verified_dyadic_generic','verified_dyadic_eight','verified_dyadic_reciprocal_eight']")
inspector=inspector.replace('Actual eight-block evaluation/product/pair composition and child multiplication paths','Actual homogeneous dyadic selection, eight-block producer and child multiplication paths')
(S/'dyadic_producer_codegen.py').write_text(inspector)
mutants=[
    ('force-unit-point','dyadic_weights(exponent,reciprocal)','dyadic_weights(0,reciprocal)'),
    ('ignore-reciprocal','dyadic_weights(exponent,reciprocal)','dyadic_weights(exponent,false)'),
    ('flip-reciprocal','dyadic_weights(exponent,reciprocal)','dyadic_weights(exponent,!reciprocal)'),
    ('replace-product-by-square','weighted_pair(even,odd,a,b,k,weights,scratch,threshold)','weighted_pair(even,odd,a,a,k,weights,scratch,threshold)'),
    ('swap-even-odd','weighted_pair(even,odd,a,b,k,weights,scratch,threshold)','weighted_pair(odd,even,a,b,k,weights,scratch,threshold)'),
    ('zero-weights','let weights=crate::toom8_evaluation::dyadic_weights(exponent,reciprocal);','let weights=[0u64;8];'),
    ('erase-even-low','weighted_pair(even,odd,a,b,k,weights,scratch,threshold);','weighted_pair(even,odd,a,b,k,weights,scratch,threshold);even[0]=0;'),
    ('erase-odd-low','weighted_pair(even,odd,a,b,k,weights,scratch,threshold);','weighted_pair(even,odd,a,b,k,weights,scratch,threshold);odd[0]=0;')]
code=(P/'check_producer.py').read_text().replace('producer_oracle','dyadic_producer_oracle').replace('producer_codegen','dyadic_producer_codegen').replace('check_producer.py','check_dyadic_producer.py')
code=code.replace('toom8_producer_runner.rs','toom8_dyadic_producer_runner.rs').replace('toom8_dyadic_producer_codegen.rs','toom8_dyadic_producer_codegen.rs')
code=code.replace('native/verified/toom8_producer.rs','native/verified/toom8_dyadic_producer.rs').replace("'toom8_producer'","'toom8_dyadic_producer'").replace('note: verifying module toom8_producer','note: verifying module toom8_dyadic_producer')
start=code.index('MUTANTS=');end=code.index('\ntag=sys.argv[1]',start);code=code[:start]+'MUTANTS='+repr(mutants)+code[end:]
code=code.replace("'scope.json','generate_convolution_spec.py','prepare_runner.py','prepare_gate.py'","'scope.json','prepare_dyadic_gate.py'")
code=code.replace('Actual eight-block evaluation and multiplication establish signed pair preconditions; not a completed Toom8 kernel','Actual homogeneous dyadic point pairs refine independent fifteen-coefficient input convolution; not a completed Toom8 kernel')
code=code.replace('Independent Python double sum of sixty-four weighted input-block products','Independent Python fifteen-coefficient convolution followed by homogeneous polynomial evaluation')
code=code.replace('Immutable eight-block producer feature gate','Immutable dyadic coefficient-bridge feature gate')
(S/'check_dyadic_producer.py').write_text(code)
origin=json.loads((S/'origin.json').read_text());origin['inherited_native_sha256']={n:h for n,h in origin['parent_native_sha256'].items() if n!='candidate/native/lib.rs'}
(S/'origin.json').write_text(json.dumps(origin,indent=2)+'\n')
scope={'status':'candidate_for_full_gate','purpose':'Establish the homogeneous coefficient interpretation from actual selected weights and actual input-block multiplication.',
       'domain':'Full-u64 equal-length inputs with 7*k <= n <= 8*k, including k=0; exponent in 0..3 and either reciprocal direction; original producer output/scratch/threshold domain.',
       'output':'Even and odd homogeneous sums of the independently defined fifteen input convolution coefficients.',
       'local_workspace':'14*(k+1) caller scratch and two separate 2*(k+1) outputs, unchanged from parent producer.',
       'local_work':'2*T_existing_forced_Toom4(k+1)+O(k); ghost power identities erase, runtime weights select fixed constants.',
       'remaining':['Endpoint removal and exact scaling','Newton producer premises and actual interpolation caller','Whole-kernel recomposition and recursion','Complete scratch lifetime and worst-case cost proof','Independent performance acceptance'],
       'benchmark_run':False,'complete_toom8':False,'production_promoted':False}
(S/'scope.json').write_text(json.dumps(scope,indent=2)+'\n')
