//! Unverified measurement driver; compile now, execute only in the granted window.
use std::{env,hint::black_box,time::Instant};
use verigmp::{arithmetic,fast_multiply};
#[link(name="gmp")]
unsafe extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
fn run(op:u32,gmp:bool,out:&mut[u64],a:&[u64],b:&[u64],work:&mut[u64],top:u32) {
    let n=a.len();
    if gmp {
        if op==0 {unsafe {__gmpn_mul_n(out.as_mut_ptr(),a.as_ptr(),b.as_ptr(),n as isize);}}
        else {
            unsafe {
                if op==2 {__gmpn_sqr(work.as_mut_ptr(),a.as_ptr(),n as isize);}
                else {__gmpn_mul_n(work.as_mut_ptr(),a.as_ptr(),b.as_ptr(),n as isize);}
            }
            out.copy_from_slice(&work[..n]);
            if top<64 {out[n-1]&=(1u64<<top)-1;}
        }
    }else {
        match op {
            0=>fast_multiply::full(out,a,b,work,black_box(24)),
            1=>arithmetic::mul_mod(out,a,b,work,top),
            2=>arithmetic::square_mod(out,a,work,top),
            _=>panic!("operation"),
        }
    }
}
fn batch(op:u32,gmp:bool,out:&mut[u64],a:&[u64],b:&[u64],work:&mut[u64],top:u32,count:u64)->u128 {
    let start=Instant::now();
    for _ in 0..count {
        run(black_box(op),black_box(gmp),black_box(&mut *out),black_box(a),black_box(b),
            black_box(&mut *work),black_box(top));
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}
fn main() {
    let args:Vec<String>=env::args().collect();assert_eq!(args.len(),8);
    let op:u32=args[1].parse().unwrap();assert!(op<=2);
    let n:usize=args[2].parse().unwrap();assert!(n>0);
    let top:u32=args[3].parse().unwrap();assert!((1..=64).contains(&top));
    let seed:u64=args[4].parse().unwrap();let gmp:bool=args[5].parse().unwrap();
    let count:u64=args[6].parse().unwrap();assert_eq!(args[7],"registered");
    let mut state=seed^(n as u64)^((top as u64)<<48)^((op as u64)<<56);
    let mut random=|| {state^=state<<13;state^=state>>7;state^=state<<17;state};
    let a:Vec<u64>=(0..n).map(|_|random()).collect();
    let b:Vec<u64>=(0..n).map(|_|random()).collect();
    let output_len=if op==0 {2*n}else{n};let capacity=match op {0=>3*n,1=>12*n,_=>10*n};
    let mut out=vec![u64::MAX;output_len];let mut work=vec![u64::MAX;capacity];
    let mut expected=vec![0;output_len];
    run(op,true,&mut expected,&a,&b,&mut work,top);
    run(op,gmp,&mut out,&a,&b,&mut work,top);assert_eq!(out,expected);
    let mut calibration=Vec::new();
    let (iterations,ns)=if count==0 {
        let mut iterations=1u64;
        loop {
            let ns=batch(op,gmp,&mut out,&a,&b,&mut work,top,iterations);
            calibration.push(format!("[{},{}]",iterations,ns));
            if ns>=20_000_000 {break(iterations,ns);}
            iterations=iterations.checked_mul(2).unwrap();
        }
    }else {(count,batch(op,gmp,&mut out,&a,&b,&mut work,top,count))};
    assert_eq!(out,expected);
    let checksum=out.iter().fold(0u64,|value,word|value.rotate_left(7)^word);
    println!("{{\"iterations\":{iterations},\"ns\":{ns},\"checksum\":{checksum},\"calibration\":[{}]}}",
             calibration.join(","));
}
