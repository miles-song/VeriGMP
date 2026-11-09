#[path="specs/radix.rs"] mod radix;
#[path="specs/precision.rs"] mod precision;
#[path="specs/product.rs"] mod product;
#[path="specs/fast_product.rs"] mod fast_product;
#[path="verified/kernel.rs"] mod kernel;
#[path="verified/limbs.rs"] mod limbs;
#[path="verified/pow2.rs"] mod pow2;
#[path="verified/multiply.rs"] mod multiply;
#[path="verified/fast_words.rs"] mod fast_words;
#[path="verified/fixed_row.rs"] mod fixed_row;
#[path="verified/fast_multiply.rs"] mod fast_multiply;
fn main() {
    use std::io::{self,BufRead,Write};
    let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines() {
        let line=line.unwrap();let mut fields=line.split_whitespace();
        let op=fields.next().unwrap();
        let args:Vec<u64>=fields.map(|s|s.parse().unwrap()).collect();
        if op=="workspace" {
            let result=fast_multiply::workspace_len(args[0].try_into().unwrap());
            writeln!(out,"{}",result.map(|x|x.to_string()).unwrap_or("none".into())).unwrap();continue;
        }
        if op=="subword" {
            let (low,borrow)=fast_words::sub_word(args[0],args[1],args[2]);
            writeln!(out,"{low} {borrow}").unwrap();continue;
        }
        if op=="abs" {
            let n:usize=args[0].try_into().unwrap();let mut dst=vec![u64::MAX;n];
            let negative=fast_words::abs_difference(&mut dst,&args[1..n+1],&args[n+1..]);
            writeln!(out,"{} {}",negative as u8,dst.iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();continue;
        }
        let top:u32=args[0].try_into().unwrap();let threshold=args[1] as usize;let mode=args[2]!=0;
        let n=(args.len()-3)/2;assert_eq!(args.len(),3+2*n);
        let a=&args[3..3+n];let b=&args[3+n..];
        let canary=0xc0ffeecafef00d17u64;
        let len=if op=="full"{2*n}else{n};
        let mut dst=vec![canary;len+2];let mut scratch=vec![canary;4*n+2];
        match op {
            "full"=>fast_multiply::full(&mut dst[1..len+1],a,b,&mut scratch[1..3*n+1],threshold),
            "mul"=>fast_multiply::modular(&mut dst[1..len+1],a,b,&mut scratch[1..4*n+1],top,threshold,8,mode),
            "default"=>fast_multiply::mul_mod(&mut dst[1..len+1],a,b,&mut scratch[1..4*n+1],top),
            "shortscratch"=>fast_multiply::mul_mod(&mut dst[1..len+1],a,b,&mut scratch[1..4*n],top),
            "square"=>fast_multiply::modular(&mut dst[1..len+1],a,a,&mut scratch[1..4*n+1],top,threshold,8,mode),
            _=>panic!("operation"),
        }
        assert_eq!(dst[0],canary);assert_eq!(dst[len+1],canary);
        assert_eq!(scratch[0],canary);assert_eq!(scratch[if op=="full"{3*n+1}else{4*n+1}],canary);
        writeln!(out,"{}",dst[1..len+1].iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
