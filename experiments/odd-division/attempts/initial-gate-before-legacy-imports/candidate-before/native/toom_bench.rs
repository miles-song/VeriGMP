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

use std::hint::black_box;use std::time::Instant;
#[link(name="gmp")] extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
fn run(square:bool,mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,low:usize){
    let n=a.len();
    if square {match mode{
        0=>fast_multiply::mul_mod(out,a,a,scratch,top),
        1|2=>{square_low::low(out,a,scratch,threshold,low,if mode==1{2}else{1});pow2::normalize_top(out,top);},
        3=>{let(product,work)=scratch.split_at_mut(2*n);toom_square::full(product,a,work,threshold);out.copy_from_slice(&product[..n]);pow2::normalize_top(out,top);},
        4=>{unsafe{__gmpn_sqr(scratch.as_mut_ptr(),a.as_ptr(),n as isize);}out.copy_from_slice(&scratch[..n]);pow2::normalize_top(out,top);},
        5=>arithmetic::square_mod(out,a,scratch,top),_=>panic!("mode"),
    }}else{match mode{
        0=>fast_multiply::mul_mod(out,a,b,scratch,top),
        1|2=>toom_low::modular(out,a,b,scratch,top,threshold,low,if mode==1{2}else{1}),
        3=>{let(product,work)=scratch.split_at_mut(2*n);toom_multiply::full(product,a,b,work,threshold);out.copy_from_slice(&product[..n]);pow2::normalize_top(out,top);},
        4=>{unsafe{__gmpn_mul_n(scratch.as_mut_ptr(),a.as_ptr(),b.as_ptr(),n as isize);}out.copy_from_slice(&scratch[..n]);pow2::normalize_top(out,top);},
        5=>arithmetic::mul_mod(out,a,b,scratch,top),_=>panic!("mode"),
    }}
}
fn batch(square:bool,mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,threshold:usize,low:usize,count:u64)->u128{
    let start=Instant::now();for _ in 0..count{
        run(black_box(square),black_box(mode),black_box(&mut *out),black_box(a),black_box(b),black_box(&mut *scratch),black_box(top),black_box(threshold),black_box(low));black_box(&*out);
    }start.elapsed().as_nanos()
}
fn main(){
    let args:Vec<String>=std::env::args().collect();let seed:u64=args[1].parse().unwrap();let tuning=args.get(2).map(|s|s=="tune").unwrap_or(false);
    let shapes:Vec<(usize,u32)>=if tuning{vec![(128,63),(256,63),(512,63),(1024,63),(2048,63),(4096,63)]}
        else{vec![(1,1),(1,64),(2,1),(23,63),(24,63),(25,63),(63,63),(64,63),(65,63),(127,63),(128,63),(129,63),
            (191,63),(192,63),(193,63),(255,63),(256,63),(257,63),(511,63),(512,63),(513,63),(1023,63),(1024,63),(1025,63),(2048,63),(4096,63)]};
    let thresholds=if tuning{vec![96,192,384]}else{vec![192]};let lows=if tuning{vec![64,128]}else{vec![128]};
    println!("square,limbs,top,threshold,low_limit,mode,repetition,iterations,ns");
    for (n,top) in shapes{
        let mut state=seed^(n as u64);let mut random=||{state^=state<<13;state^=state>>7;state^=state<<17;state};
        let a:Vec<u64>=(0..n).map(|_|random()).collect();let b:Vec<u64>=(0..n).map(|_|random()).collect();
        let mut out=vec![0;n];let mut scratch=vec![0;14*n];
        for sq in [false,true]{
            let mut expected=vec![0;n];run(sq,4,&mut expected,&a,&b,&mut scratch,top,192,128);
            for t in &thresholds{for low in &lows{
                let mut counts=[1u64;6];
                for mode in 0..6{run(sq,mode,&mut out,&a,&b,&mut scratch,top,*t,*low);assert_eq!(out,expected);
                    while batch(sq,mode,&mut out,&a,&b,&mut scratch,top,*t,*low,counts[mode as usize])<if tuning{5_000_000}else{10_000_000}{counts[mode as usize]*=2;}}
                for rep in 0..if tuning{3}else{7}{for j in 0..6{let mode=(j+rep)%6;let mut count=counts[mode as usize];
                    let mut ns=batch(sq,mode,&mut out,&a,&b,&mut scratch,top,*t,*low,count);
                    while !tuning && ns<10_000_000 {
                        count=count.checked_mul(2).expect("benchmark iteration capacity");
                        ns=batch(sq,mode,&mut out,&a,&b,&mut scratch,top,*t,*low,count);
                    }
                    counts[mode as usize]=count;assert_eq!(out,expected);
                    println!("{},{n},{top},{t},{low},{mode},{rep},{count},{ns}",sq as u32);}}
            }}
        }
    }
}

#[path="specs/square_base.rs"] mod square_base_spec;
#[path="verified/square_base.rs"] mod square_base;
