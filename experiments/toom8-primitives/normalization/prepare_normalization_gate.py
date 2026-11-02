from pathlib import Path
import json
S=Path(__file__).resolve().parent;P=S.parent/'toom8-dyadic-producer-stage-e22a4dd'
imports=(S/'candidate/native/lib.rs').read_text()
old=(P/'candidate/native/toom8_dyadic_producer_runner.rs').read_text();body=old[old.index('\nfn words'):]
body=body.replace('assert_eq!(f.len(),8);assert_eq!(f[0],"dyadic")','assert_eq!(f.len(),7);assert_eq!(f[0],"normalized")')
body=body.replace('let exponent:u32=f[3].parse().unwrap();assert!(exponent<=3);let reciprocal:u32=f[4].parse().unwrap();assert!(reciprocal<=1);','let node:u32=f[3].parse().unwrap();assert!(node<6);')
body=body.replace('words(f[5]);let b=words(f[6])','words(f[4]);let b=words(f[5])').replace('let extra:usize=f[7]','let extra:usize=f[6]').replace('checked_mul(14)','checked_mul(18)')
body=body.replace('toom8_dyadic_producer::dyadic_pair','toom8_normalization::prepare_pair').replace('&a,&b,k,exponent,reciprocal!=0,','&a,&b,k,node,')
(S/'candidate/native/toom8_normalization_runner.rs').write_text(imports+body)
wrappers='''
#[no_mangle] pub fn verified_normalization_generic(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,node:u32,s:&mut[u64]){toom8_normalization::prepare_pair(e,o,a,b,k,node,s,24);}
#[no_mangle] pub fn verified_normalization_reciprocal_eight(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_normalization::prepare_pair(e,o,a,b,k,0,s,24);}
#[no_mangle] pub fn verified_normalization_four(e:&mut[u64],o:&mut[u64],a:&[u64],b:&[u64],k:usize,s:&mut[u64]){toom8_normalization::prepare_pair(e,o,a,b,k,5,s,24);}
fn main(){}
'''
(S/'candidate/native/toom8_normalization_codegen.rs').write_text(imports+wrappers)
inspector=(P/'dyadic_producer_codegen.py').read_text().replace("['verified_dyadic_generic','verified_dyadic_eight','verified_dyadic_reciprocal_eight']","['verified_normalization_generic','verified_normalization_reciprocal_eight','verified_normalization_four']").replace('Actual homogeneous dyadic selection, eight-block producer and child multiplication paths','Actual endpoint products, signed point-pair production, exact normalization and child multiplication paths')
(S/'normalization_codegen.py').write_text(inspector)
mutants=[
    ('skip-low-endpoint','scaled_subtraction::sub_scaled_exact(even,low,low_word);',''),
    ('skip-high-endpoint','scaled_subtraction::sub_scaled_exact(even,high,high_word);',''),
    ('wrong-low-multiplier','scaled_subtraction::sub_scaled_exact(even,low,low_word);','scaled_subtraction::sub_scaled_exact(even,low,high_word);'),
    ('skip-even-division','toom_words::divide_exact(even,even_divisor);',''),
    ('wrong-odd-divisor','toom_words::divide_exact(odd,odd_divisor);','toom_words::divide_exact(odd,even_divisor);'),
    ('skip-even-scale','toom_words::scale_exact(even,even_scale);',''),
    ('skip-odd-scale','toom_words::scale_exact(odd,odd_scale);',''),
    ('wrong-node-parameters','let (exponent,reciprocal,_,_,_,_,_,_)=parameters(node);','let (exponent,reciprocal,_,_,_,_,_,_)=parameters(0);'),
    ('square-low-endpoint','toom4_multiply::full(low,&a[..k],&b[..k],work,threshold);','toom4_multiply::full(low,&a[..k],&a[..k],work,threshold);'),
    ('erase-high-endpoint','toom4_multiply::full(high,&a[7*k..],&b[7*k..],work,threshold);','toom_words::zero(high);'),
    ('swap-shared-endpoints','with_endpoints(even,odd,a,b,low,high,k,node,work,threshold);','with_endpoints(even,odd,a,b,high,low,k,node,work,threshold);'),
    ('flip-dyadic-direction','dyadic_pair(even,odd,a,b,k,exponent,reciprocal,scratch,threshold);','dyadic_pair(even,odd,a,b,k,exponent,!reciprocal,scratch,threshold);')]
code=(P/'check_dyadic_producer.py').read_text().replace('dyadic_producer_oracle','normalization_oracle').replace('dyadic_producer_codegen','normalization_codegen').replace('check_dyadic_producer.py','check_normalization.py')
code=code.replace('toom8_dyadic_producer_runner.rs','toom8_normalization_runner.rs').replace('native/verified/toom8_dyadic_producer.rs','native/verified/toom8_normalization.rs').replace("'toom8_dyadic_producer'","'toom8_normalization'").replace('note: verifying module toom8_dyadic_producer','note: verifying module toom8_normalization')
start=code.index('MUTANTS=');end=code.index('\ntag=sys.argv[1]',start);code=code[:start]+'MUTANTS='+repr(mutants)+code[end:]
code=code.replace("'scope.json','prepare_dyadic_gate.py'","'scope.json','prepare_normalization_gate.py','generate_normalization_spec.py'")
code=code.replace('Actual homogeneous dyadic point pairs refine independent fifteen-coefficient input convolution; not a completed Toom8 kernel','Actual endpoint products and exact homogeneous normalization establish the six paired Newton node values from input convolution; not a completed Toom8 kernel')
code=code.replace('Independent Python fifteen-coefficient convolution followed by homogeneous polynomial evaluation','Independent Python input convolution and scaled even/odd coefficient polynomials at six Newton nodes')
(S/'check_normalization.py').write_text(code)
origin=json.loads((S/'origin.json').read_text());origin['inherited_native_sha256']={n:h for n,h in origin['parent_native_sha256'].items() if n!='candidate/native/lib.rs'}
(S/'origin.json').write_text(json.dumps(origin,indent=2)+'\n')
development=(S/'check_development.py').read_text().replace("entry='toom8_producer_runner.rs'","entry='toom8_normalization_runner.rs'").replace("else 'toom8_producer_codegen.rs'","else 'toom8_normalization_codegen.rs'")
(S/'check_development.py').write_text(development)
scope={'status':'candidate_for_full_gate','purpose':'Derive endpoint subtraction, exact divisibility, scale capacity and the six even/odd Newton node expressions from actual input-block products.',
    'domain':'Full-u64 equal-length input slices with 7*k<=n<=8*k, including k=0 and empty final block; node0..5 represents p/q=1/8,1/4,1/2,1,2,4; original child threshold>=24.',
    'execution':'Two actual endpoint products (empty endpoints handled without a nonempty multiplication call), two actual signed-point products, endpoint subtraction, exact division by powers of two and exact scaling.',
    'shared_endpoint_interface':'with_endpoints retains proven actual endpoint values and uses two point products. A final kernel may reuse two endpoint products across all six pairs.',
    'local_workspace':'prepare_pair proves caller scratch>=18*(k+1), split into 2*k and 2*h endpoint buffers and at least14*(k+1) child scratch. with_endpoints uses the original14*(k+1) scratch. Two2*(k+1) output slices are separate.',
    'local_work':'Self-contained one-node composition has T(k)+T(h)+2*T(k+1)+O(k) existing child work, skipping empty endpoints. The shared-endpoint interface has2*T(k+1)+O(k). No checked machine-cost theorem or whole-kernel scratch proof is claimed.',
    'fifteen_product_boundary':'The future kernel uses endpoints2+six paired nodes12+positive-eight1. No negative-eight product is introduced by this feature.',
    'remaining':['Actual six-node Newton caller and seventh odd node','Full recomposition and decreasing Toom8 recursion','Whole scratch lifetime/cost proof','Independent performance acceptance'],
    'benchmark_run':False,'complete_toom8':False,'production_promoted':False}
(S/'scope.json').write_text(json.dumps(scope,indent=2)+'\n')
