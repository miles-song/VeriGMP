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
        let out=if op=="subscaled"{
            assert!(args.len()>=3);let word=args[0];let n=usize::try_from(args[1]).unwrap();let m=usize::try_from(args[2]).unwrap();
            assert_eq!(args.len(),3+n+m);let mut out=vec![u64::MAX;n+2];out[1..n+1].copy_from_slice(&args[3..3+n]);
            let mut rhs=vec![u64::MAX;m+2];rhs[1..m+1].copy_from_slice(&args[3+n..]);
            toom_words::sub_scaled_exact(&mut out[1..n+1],&rhs[1..m+1],word);
            assert_eq!((out[0],out[n+1]),(u64::MAX,u64::MAX));
            assert_eq!((rhs[0],rhs[m+1]),(u64::MAX,u64::MAX));assert_eq!(&rhs[1..m+1],&args[3+n..]);
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
            let full=matches!(op,"full"|"squarefull"|"squarek");let size=if full{2*n}else{n};
            let capacity=match op{"squarek"=>3*n,"squarefull"|"squarelow"|"square"=>10*n,_=>12*n};
            let mut out=vec![u64::MAX;size+2];let mut scratch=vec![u64::MAX;capacity+2];
            let dst=&mut out[1..size+1];let work=&mut scratch[1..capacity+1];
            match op{
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
