//! Verified arithmetic on caller-owned little-endian u64 slices.
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

#[path="specs/toom8_evaluation.rs"] pub mod toom8_evaluation_spec;
#[path="verified/toom8_evaluation.rs"] pub mod toom8_evaluation;

#[path="specs/toom8_pair.rs"] pub mod toom8_pair_spec;
#[path="verified/toom8_pair.rs"] pub mod toom8_pair;

#[path="specs/toom8_producer.rs"] pub mod toom8_producer_spec;
#[path="verified/toom8_producer.rs"] pub mod toom8_producer;

#[path="specs/toom8_convolution.rs"] pub mod toom8_convolution;

#[path="specs/toom8_dyadic_producer.rs"] pub mod toom8_dyadic_producer_spec;
#[path="verified/toom8_dyadic_producer.rs"] pub mod toom8_dyadic_producer;

#[path="specs/toom8_normalization.rs"] pub mod toom8_normalization_spec;
#[path="verified/toom8_normalization.rs"] pub mod toom8_normalization;

#[path="verified/toom8_even.rs"]
pub mod toom8_even;

#[path="specs/toom8_seventh.rs"] pub mod toom8_seventh_spec;
#[path="verified/toom8_seventh.rs"] pub mod toom8_seventh;

#[path="verified/toom8_interpolation.rs"] pub mod toom8_interpolation;

#[path="specs/toom8_recomposition.rs"] pub mod toom8_recomposition_spec;
#[path="verified/toom8_recomposition.rs"] pub mod toom8_recomposition;

#[path="verified/toom8_product.rs"] pub mod toom8_product;

fn words(s:&str)->Vec<u64>{if s=="-"{vec![]}else{s.split(',').map(|x|x.parse().unwrap()).collect()}}
fn main(){
    use std::io::{self,BufRead,Write};let mut out=io::BufWriter::new(io::stdout().lock());
    for line in io::stdin().lock().lines(){
        let line=line.unwrap();let f:Vec<&str>=line.split('|').collect();assert_eq!(f.len(),6);
        let mode=f[0];assert!(matches!(mode,"balanced"|"balanced-alias"|"full"|"full-alias"));
        let parameter:usize=f[1].parse().unwrap();let child:usize=f[2].parse().unwrap();assert!(child>=24);
        let a=words(f[3]);let b=words(f[4]);assert_eq!(a.len(),b.len());
        let extra:usize=f[5].parse().unwrap();assert!(extra<=64);let n=a.len();
        let width=if mode.starts_with("balanced"){
            assert!(parameter.checked_mul(7).unwrap()<=n && n<=parameter.checked_mul(8).unwrap());
            parameter.checked_add(1).unwrap().checked_mul(44).unwrap()
        }else{assert!(n>0 && parameter>=56);n.checked_mul(12).unwrap()};
        if mode.ends_with("alias"){assert_eq!(a,b);}
        let before_a=a.clone();let before_b=b.clone();let marker=0x55aa55aa55aa55aau64;
        let mut dst=vec![marker;n.checked_mul(2).unwrap()+2];let mut scratch=vec![marker;width+extra+2];
        let input_b=if mode.ends_with("alias"){&a[..]}else{&b[..]};
        if mode.starts_with("balanced"){
            toom8_product::balanced(&mut dst[1..2*n+1],&a,input_b,parameter,&mut scratch[1..width+extra+1],child);
        }else{
            toom8_product::full(&mut dst[1..2*n+1],&a,input_b,&mut scratch[1..width+extra+1],parameter,child);
        }
        assert_eq!(a,before_a);assert_eq!(b,before_b);
        assert_eq!(dst[0],marker);assert_eq!(dst[2*n+1],marker);assert_eq!(scratch[0],marker);assert_eq!(scratch[width+extra+1],marker);
        writeln!(out,"{}",dst[1..2*n+1].iter().map(u64::to_string).collect::<Vec<_>>().join(" ")).unwrap();
    }
}
