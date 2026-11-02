#[path="specs/radix.rs"] pub mod radix;
#[path="specs/precision.rs"] pub mod precision;
#[path="specs/product.rs"] pub mod product;
#[path="specs/fast_product.rs"] pub mod fast_product;
#[path="verified/kernel.rs"] pub mod kernel;
#[path="verified/limbs.rs"] pub mod limbs;
#[path="verified/pow2.rs"] pub mod pow2;
#[path="verified/multiply.rs"] pub mod multiply;
#[path="verified/fast_words.rs"] pub mod fast_words;
#[path="verified/fast_multiply.rs"] pub mod fast_multiply;
#[path="specs/toom.rs"] pub mod toom;
#[path="specs/toom_blocks.rs"] pub mod toom_blocks;
#[path="specs/square.rs"] pub mod square_spec;
#[path="verified/toom_words.rs"] pub mod toom_words;
#[path="verified/toom_evaluate.rs"] pub mod toom_evaluate;
#[path="verified/toom_interpolate.rs"] pub mod toom_interpolate;
#[path="verified/toom_multiply.rs"] pub mod toom_multiply;
#[path="verified/toom_low.rs"] pub mod toom_low;
#[path="verified/square.rs"] pub mod square;
#[path="verified/toom_square.rs"] pub mod toom_square;
#[path="verified/square_low.rs"] pub mod square_low;
#[path="verified/mac4.rs"] pub mod mac4;
#[path="verified/arithmetic.rs"] pub mod arithmetic;

#[path="specs/square_base.rs"] pub mod square_base_spec;
#[path="verified/square_base.rs"] pub mod square_base;
#[path="specs/toom4.rs"] pub mod toom4;
#[path="verified/toom4_interpolate.rs"] pub mod toom4_interpolate;
#[path="verified/toom4_evaluate.rs"] pub mod toom4_evaluate;
#[path="specs/toom4_blocks.rs"] pub mod toom4_blocks;
#[path="verified/toom4_multiply.rs"] pub mod toom4_multiply;
#[path="verified/toom4_square.rs"] pub mod toom4_square;
#[path="verified/toom4_low.rs"] pub mod toom4_low;
#[path="verified/toom4_square_low.rs"] pub mod toom4_square_low;
#[path="verified/toom4_candidate.rs"] pub mod toom4_candidate;

#[path="specs/odd_division.rs"] pub mod odd_division_spec;
#[path="verified/odd_division.rs"] pub mod odd_division;

#[path="verified/scaled_subtraction.rs"] pub mod scaled_subtraction;

#[path="specs/signed_evaluation.rs"] pub mod signed_evaluation_spec;
#[path="verified/signed_evaluation.rs"] pub mod signed_evaluation;

#[path="specs/wide_odd_division.rs"] pub mod wide_odd_division_spec;
#[path="verified/wide_odd_division.rs"] pub mod wide_odd_division;

#[path="specs/toom8_newton.rs"] pub mod toom8_newton_spec;
#[path="verified/toom8_newton.rs"] pub mod toom8_newton;
fn main(){
    use std::io::{self,BufRead,Write};
    let mut output=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let args:Vec<u64>=line.split_whitespace().map(|s|s.parse().unwrap()).collect();
        assert!(args.len()>=2);let degree=args[0] as usize;assert!(degree==5 || degree==6);
        let n=usize::try_from(args[1]).unwrap();assert_eq!(args.len(),2usize.checked_add((degree+1).checked_mul(n).unwrap()).unwrap());
        let mut buffers:[Vec<u64>;7]=std::array::from_fn(|_|vec![u64::MAX;n.checked_add(2).unwrap()]);
        for i in 0..degree+1 {buffers[i][1..n+1].copy_from_slice(&args[2+i*n..2+(i+1)*n]);}
        let saved_extra=buffers[6].clone();let [a0,a1,a2,a3,a4,a5,a6]=&mut buffers;
        if degree==5 {toom8_newton::even(&mut a0[1..n+1],&mut a1[1..n+1],&mut a2[1..n+1],&mut a3[1..n+1],&mut a4[1..n+1],&mut a5[1..n+1]);}
        else {toom8_newton::odd(&mut a0[1..n+1],&mut a1[1..n+1],&mut a2[1..n+1],&mut a3[1..n+1],&mut a4[1..n+1],&mut a5[1..n+1],&mut a6[1..n+1]);}
        if degree==5 {assert_eq!(buffers[6],saved_extra);}
        for (i,buf) in buffers[..degree+1].iter().enumerate(){
            assert_eq!((buf[0],buf[n+1]),(u64::MAX,u64::MAX));
            for (j,value) in buf[1..n+1].iter().enumerate(){if i*n+j>0{write!(output," ").unwrap();}write!(output,"{}",value).unwrap();}
        }
        writeln!(output).unwrap();
    }
}
