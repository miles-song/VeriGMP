use verigmp::{arithmetic, mac4, pow2, square, square_base, square_low,
    toom4_candidate, toom4_evaluate, toom4_low, toom4_multiply, toom4_square,
    toom4_square_low, toom_low, toom_multiply, toom_square, toom_words};
use verigmp::{precision::{modulus, modulus_properties}, radix::value};
use vstd::prelude::*;
use vstd::arithmetic::div_mod::*;
use vstd::arithmetic::power2::*;

verus! {
fn imported_product(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=12*a@.len(),1<=top<=64,
    ensures value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
{
    toom4_candidate::mul_mod(dst,a,b,scratch,top);
}

fn imported_square(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
{
    toom4_candidate::square_mod(dst,a,scratch,top);
}

fn imported_forced_product(dst:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,a@.len()==b@.len(),old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=12*a@.len(),1<=top<=64,
    ensures value(final(dst)@)==(value(a@)*value(b@))%modulus(a@.len(),top as nat),
{
    toom4_low::modular(dst,a,b,scratch,top,256,128,2);
}

fn imported_forced_square(dst:&mut[u64],a:&[u64],scratch:&mut[u64],top:u32)
    requires a@.len()>0,old(dst)@.len()==a@.len(),
        old(scratch)@.len()>=10*a@.len(),1<=top<=64,
    ensures value(final(dst)@)==(value(a@)*value(a@))%modulus(a@.len(),top as nat),
{
    assert!(1<=top && top<=64);
    toom4_square_low::low(dst,a,scratch,256,64,1);
    pow2::normalize_top(dst,top);
    proof {
        modulus_properties(a@.len(),top as nat);
        lemma_pow2_pos((64-top) as nat);
        lemma_mod_mod(value(a@)*value(a@),modulus(a@.len(),top as nat),pow2((64-top) as nat) as int);
    }
}
}

fn main(){
    use std::io::{self,BufRead,Write};
    let mut output=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let mut fields=line.split_whitespace();
        let op=fields.next().unwrap();let args:Vec<u64>=fields.map(|s|s.parse().unwrap()).collect();
        let out=if op=="weighted4"||op=="signed4"{
            let signed=op=="signed4";let off=if signed{1}else{4};
            assert!(args.len()>=off+2);let n=args[off] as usize;let h=args[off+1] as usize;
            assert!(h<=n && args.len()==off+2+3*n+h);let inputs=&args[off+2..];
            let a0=&inputs[..n];let a1=&inputs[n..2*n];let a2=&inputs[2*n..3*n];let a3=&inputs[3*n..];
            let mut out=vec![u64::MAX;n+3];let mut temp=vec![u64::MAX;n+3];let saved=inputs.to_vec();
            let neg=if signed{
                assert!(args[0]<=1);toom4_evaluate::signed(&mut out[1..n+2],&mut temp[1..n+2],a0,a1,a2,a3,args[0]!=0)
            }else{
                toom4_evaluate::weighted(&mut out[1..n+2],a0,a1,a2,a3,args[0],args[1],args[2],args[3]);false
            };
            assert_eq!((out[0],out[n+2],temp[0],temp[n+2]),(u64::MAX,u64::MAX,u64::MAX,u64::MAX));
            assert_eq!(saved,inputs);let mut answer=out[1..n+2].to_vec();if signed{answer.push(neg as u64);}answer
        }else if op=="divide"{
            let mut out=args[1..].to_vec();let rem=toom_words::divide_word(&mut out,args[0]);out.push(rem);out
        }else if op=="squarebaselow"{
            assert!(!args.is_empty());let n=args.len();let mut out=vec![u64::MAX;n+2];
            square_base::low(&mut out[1..n+1],&args);
            assert_eq!((out[0],out[n+1]),(u64::MAX,u64::MAX));out[1..n+1].to_vec()
        }else if op=="squarebase"{
            assert!(!args.is_empty());let n=args.len();let mut out=vec![u64::MAX;2*n+2];
            square_base::full(&mut out[1..2*n+1],&args);
            assert_eq!((out[0],out[2*n+1]),(u64::MAX,u64::MAX));out[1..2*n+1].to_vec()
        }else if op=="workspace"{
            let n=usize::try_from(args[0]).unwrap();
            vec![arithmetic::workspace_len(n).unwrap_or(0) as u64,arithmetic::square_workspace_len(n).unwrap_or(0) as u64]
        }else if op=="row"{
            let word=args[0];let n=usize::try_from(args[1]).unwrap();let m=usize::try_from(args[2]).unwrap();
            assert_eq!(args.len(),3+n+m);let mut out=vec![u64::MAX;n+2];out[1..n+1].copy_from_slice(&args[3..3+n]);
            let carry=mac4::add_mul_word(&mut out[1..n+1],&args[3+n..],word);
            assert_eq!((out[0],out[n+1]),(u64::MAX,u64::MAX));let mut out=out[1..n+1].to_vec();out.push(carry);out
        }else{
            assert!(args.len()>=6 && (args.len()-4)%2==0);
            let top=u32::try_from(args[0]).unwrap();let threshold=usize::try_from(args[1]).unwrap();
            let low=usize::try_from(args[2]).unwrap();let split=u32::try_from(args[3]).unwrap();let n=(args.len()-4)/2;
            let a=&args[4..4+n];let b=&args[4+n..];
            let full=matches!(op,"full"|"squarefull"|"squarek"|"full4"|"full4same"|"squarefull4"|"shortscratch4");let size=if full{2*n}else{n};
            let capacity=match op{"squarek"=>3*n,"squarefull"|"squarelow"|"square"|"squarefull4"|"squarelow4"|"candidate4square"|"forced4square"=>10*n,_=>12*n};
            let mut out=vec![u64::MAX;size+2];let mut scratch=vec![u64::MAX;capacity+2];
            let dst=&mut out[1..size+1];let work=&mut scratch[1..capacity+1];
            match op{
                "full4"=>toom4_multiply::full(dst,a,b,work,threshold),
                "full4same"=>toom4_multiply::full(dst,a,a,work,threshold),
                "squarefull4"=>toom4_square::full(dst,a,work,threshold),
                "low4"=>toom4_low::modular(dst,a,b,work,top,threshold,low,split),
                "squarelow4"=>{toom4_square_low::low(dst,a,work,threshold,low,split);pow2::normalize_top(dst,top);},
                "candidate4"=>imported_product(dst,a,b,work,top),
                "candidate4same"=>imported_product(dst,a,a,work,top),
                "candidate4square"=>imported_square(dst,a,work,top),
                "forced4"=>imported_forced_product(dst,a,b,work,top),
                "forced4same"=>imported_forced_product(dst,a,a,work,top),
                "forced4square"=>imported_forced_square(dst,a,work,top),
                "shortscratch4"=>toom4_multiply::full(dst,a,b,&mut work[..12*n-1],threshold),
                "full"=>toom_multiply::full(dst,a,b,work,threshold),
                "low"=>toom_low::modular(dst,a,b,work,top,threshold,low,split),
                "default"=>arithmetic::mul_mod(dst,a,b,work,top),
                "same"=>arithmetic::mul_mod(dst,a,a,work,top),
                "shortscratch"=>arithmetic::mul_mod(dst,a,b,&mut work[..3*n],top),
                "squarefull"=>toom_square::full(dst,a,work,threshold),
                "squarek"=>square::full(dst,a,work,threshold),
                "squarelow"=>{square_low::low(dst,a,work,threshold,low,split);pow2::normalize_top(dst,top);},
                "square"=>arithmetic::square_mod(dst,a,work,top),
                _=>panic!("operation"),
            }
            assert_eq!((out[0],out[size+1]),(u64::MAX,u64::MAX));
            assert_eq!((scratch[0],scratch[capacity+1]),(u64::MAX,u64::MAX));out[1..size+1].to_vec()
        };
        writeln!(output,"{}",out.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
