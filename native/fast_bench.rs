//! Runtime inputs, reused output/scratch, interleaved same-process timing.
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
#[path="controls/fast_multiply.rs"] mod ordinary;
use std::hint::black_box;
use std::time::Instant;

#[link(name="gmp")]
extern "C" { fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize); }

fn run(mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,low_limit:usize) {
    match mode {
        0=>multiply::mul_mod(out,a,b,top),
        1|2=>fast_multiply::modular(out,a,b,scratch,top,threshold,low_limit,mode==2),
        3=>{let n=a.len();let (product,work)=scratch.split_at_mut(2*n);
            fast_multiply::full(product,a,b,work,threshold);out.copy_from_slice(&product[..n]);pow2::normalize_top(out,top);},
        4=>{unsafe {__gmpn_mul_n(scratch.as_mut_ptr(),a.as_ptr(),b.as_ptr(),a.len() as isize);}
            out.copy_from_slice(&scratch[..a.len()]);pow2::normalize_top(out,top);},
        5=>ordinary::modular(out,a,b,scratch,top,threshold,low_limit),
        6=>fast_multiply::mul_mod(out,a,b,scratch,top),
        _=>panic!("mode"),
    }
}

fn batch(mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,low_limit:usize,count:u64)->u128 {
    let start=Instant::now();
    for _ in 0..count {
        run(black_box(mode),black_box(&mut *out),black_box(a),black_box(b),black_box(&mut *scratch),black_box(top),black_box(threshold),black_box(low_limit));
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}
fn main() {
    let args:Vec<String>=std::env::args().collect();
    let seed:u64=args[1].parse().unwrap();let tuning=args.get(2).map(|s|s=="tune").unwrap_or(false);
    let shapes:Vec<(usize,u32)>=if tuning {vec![(32,63),(64,63),(128,63),(256,63),(512,63),(1024,63),(2048,63)]}
        else {vec![(1,1),(1,64),(2,1),(15,63),(16,63),(17,63),(23,63),(24,63),(25,63),(31,63),(32,63),(33,63),
            (63,63),(64,63),(65,63),(127,63),(128,63),(129,63),(255,63),(256,63),(257,63),
            (511,63),(512,63),(513,63),(1023,63),(1024,63),(1025,63),(2048,63),(4096,63)]};
    let thresholds:Vec<usize>=if tuning {vec![16,24,32]}else{vec![24]};
    let low_limits=if tuning{vec![32,64,96,128]}else{vec![64]};
    println!("limbs,top,threshold,low_limit,mode,repetition,iterations,ns");
    for (n,top) in shapes {
        let mut state=seed^(n as u64);
        let mut random=||{state^=state<<13;state^=state>>7;state^=state<<17;state};
        let a:Vec<u64>=(0..n).map(|_|random()).collect();let b:Vec<u64>=(0..n).map(|_|random()).collect();
        // Full-then-truncate mode needs 2n result plus 3n child work; low needs only 4n.
        let mut out=vec![0;n];let mut scratch=vec![0;5*n];
        let mut expected=vec![0;n];run(4,&mut expected,&a,&b,&mut scratch,top,24,64);
        for threshold in &thresholds { for low_limit in &low_limits {
            let modes=if tuning{6}else{7};
            let mut counts=[1u64;7];
            for mode in 0..modes {run(mode,&mut out,&a,&b,&mut scratch,top,*threshold,*low_limit);assert_eq!(out,expected);
                loop {if batch(mode,&mut out,&a,&b,&mut scratch,top,*threshold,*low_limit,counts[mode as usize])>=if tuning{5_000_000}else{15_000_000}{break;}
                    counts[mode as usize]*=2;}
            }
            for rep in 0..if tuning{3}else{7} {
                for j in 0..modes {let mode=(j+rep)%modes;let count=counts[mode as usize];
                    let ns=batch(mode,&mut out,&a,&b,&mut scratch,top,*threshold,*low_limit,count);assert_eq!(out,expected);
                    println!("{n},{top},{threshold},{low_limit},{mode},{rep},{count},{ns}");}
            }
        }}
    }
}
