#[path="specs/radix.rs"] mod radix;
#[path="specs/precision.rs"] mod precision;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="specs/toom.rs"] mod toom;
#[path="specs/toom_blocks.rs"] mod toom_blocks;
#[path="specs/square.rs"] mod square_spec;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/toom_words.rs"] mod toom_words;
#[path="verified/toom_evaluate.rs"] mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] mod toom_interpolate;
#[path="verified/fast_multiply.rs"] mod fast_multiply;
#[path="verified/toom_multiply.rs"] mod toom_multiply;
#[path="verified/toom_low.rs"] mod toom_low;
#[path="verified/square.rs"] mod square;
#[path="verified/toom_square.rs"] mod toom_square;
#[path="verified/square_low.rs"] mod square_low;
#[path="verified/mac4.rs"] mod mac4;
#[path="verified/arithmetic.rs"] mod arithmetic;

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
        }else if op=="oddlimb"{
            assert_eq!(args.len(),3);let divisor=args[0];let carry=args[1];let x=args[2];
            assert!(matches!(divisor,3|9|15) && carry<divisor);
            let inv=match divisor{3=>12297829382473034411,9=>10248191152060862009,_=>17216961135462248175};
            let (q,next)=odd_division::quotient_limb(x,carry,divisor,inv);vec![q,next]
        }else if op=="exactodd"||op=="exactapi"{
            assert!(!args.is_empty());let divisor=args[0];assert!(divisor>0);
            if op=="exactodd"{assert!(matches!(divisor,3|9|15));}
            let input=&args[1..];let saved=input.to_vec();let n=input.len();let mut rem=0u128;
            for x in input.iter().rev(){rem=((rem<<64)+(*x as u128))%(divisor as u128);}
            assert_eq!(rem,0);let mut out=vec![u64::MAX;n+2];out[1..n+1].copy_from_slice(input);
            if op=="exactodd"{odd_division::divide_exact_odd(&mut out[1..n+1],divisor);}
            else{toom_words::divide_exact(&mut out[1..n+1],divisor);}
            assert_eq!((out[0],out[n+1]),(u64::MAX,u64::MAX));assert_eq!(saved,input);
            out[1..n+1].to_vec()
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
            let capacity=match op{"squarek"=>3*n,"squarefull"|"squarelow"|"square"|"squarefull4"|"squarelow4"|"candidate4square"=>10*n,_=>12*n};
            let mut out=vec![u64::MAX;size+2];let mut scratch=vec![u64::MAX;capacity+2];
            let dst=&mut out[1..size+1];let work=&mut scratch[1..capacity+1];
            match op{
                "full4"=>toom4_multiply::full(dst,a,b,work,threshold),
                "full4same"=>toom4_multiply::full(dst,a,a,work,threshold),
                "squarefull4"=>toom4_square::full(dst,a,work,threshold),
                "low4"=>toom4_low::modular(dst,a,b,work,top,threshold,low,split),
                "squarelow4"=>{toom4_square_low::low(dst,a,work,threshold,low,split);pow2::normalize_top(dst,top);},
                "candidate4"=>toom4_candidate::mul_mod(dst,a,b,work,top),
                "candidate4square"=>toom4_candidate::square_mod(dst,a,work,top),
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

#[path="specs/square_base.rs"] mod square_base_spec;
#[path="verified/square_base.rs"] mod square_base;

#[path="specs/toom4.rs"] mod toom4;
#[path="verified/toom4_interpolate.rs"] mod toom4_interpolate;
#[path="verified/toom4_evaluate.rs"] mod toom4_evaluate;
#[path="specs/toom4_blocks.rs"] mod toom4_blocks;
#[path="verified/toom4_multiply.rs"] mod toom4_multiply;
#[path="verified/toom4_square.rs"] mod toom4_square;
#[path="verified/toom4_low.rs"] mod toom4_low;
#[path="verified/toom4_square_low.rs"] mod toom4_square_low;
#[path="verified/toom4_candidate.rs"] mod toom4_candidate;

#[path="specs/odd_division.rs"] mod odd_division_spec;
#[path="verified/odd_division.rs"] mod odd_division;
