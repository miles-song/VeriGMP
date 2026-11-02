extern crate baseline;
extern crate candidate;
use std::hint::black_box;
use std::time::Instant;
#[link(name="gmp")] extern "C" {
    fn __gmpn_mul_n(out:*mut u64,a:*const u64,b:*const u64,n:isize);
    fn __gmpn_sqr(out:*mut u64,a:*const u64,n:isize);
}
fn run(op:u32,mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32){
    match (op,mode) {
        (0,0)=>baseline::arithmetic::mul_mod(out,a,b,scratch,top),
        (0,1)=>candidate::arithmetic::mul_mod(out,a,b,scratch,top),
        (1,0)=>baseline::arithmetic::square_mod(out,a,scratch,top),
        (1,1)=>candidate::arithmetic::square_mod(out,a,scratch,top),
        (2,0)=>baseline::fast_multiply::base_low(out,a,a),
        (2,1)=>candidate::square_base::low(out,a),
        (_,2)=>{
            unsafe{if op==0{__gmpn_mul_n(scratch.as_mut_ptr(),a.as_ptr(),b.as_ptr(),a.len() as isize);}
                else{__gmpn_sqr(scratch.as_mut_ptr(),a.as_ptr(),a.len() as isize);}}
            out.copy_from_slice(&scratch[..a.len()]);
            if top<64{*out.last_mut().unwrap()&=(1u64<<top)-1;}
        },
        _=>panic!("operation/mode"),
    }
}
fn batch(op:u32,mode:u32,out:&mut[u64],a:&[u64],b:&[u64],scratch:&mut[u64],top:u32,count:u64)->u128{
    let start=Instant::now();
    for _ in 0..count {
        run(black_box(op),black_box(mode),black_box(&mut *out),black_box(a),black_box(b),black_box(&mut *scratch),black_box(top));
        black_box(&*out);
    }
    start.elapsed().as_nanos()
}
fn main(){
    let leaf=false;
    let shapes:Vec<(usize,u32)>=[3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,23,24,25,31,32,33,48,63,64,65,96,127,128].iter().map(|&n|(n,63)).collect();
    println!("operation,limbs,top,mode,repetition,iterations,ns");
    for (n,top) in shapes {
        let mut state=16438731u64^(n as u64);let mut random=||{state^=state<<13;state^=state>>7;state^=state<<17;state};
        let a:Vec<_>=(0..n).map(|_|random()).collect();let b:Vec<_>=(0..n).map(|_|random()).collect();
        let mut out=vec![u64::MAX;n];let mut scratch=vec![0;14*n];
        for op in [1u32] {
            let mut expected=vec![0;n];run(op,2,&mut expected,&a,&b,&mut scratch,top);
            let mut counts=[1u64;3];
            for mode in 0..3 {
                run(op,mode,&mut out,&a,&b,&mut scratch,top);assert_eq!(out,expected);
                while batch(op,mode,&mut out,&a,&b,&mut scratch,top,counts[mode as usize])<10_000_000 {
                    counts[mode as usize]=counts[mode as usize].checked_mul(2).unwrap();
                }
            }
            for rep in 0..7 {for j in 0..3 {
                let mode=(j+rep)%3;
                let elapsed=loop{
                    let elapsed=batch(op,mode,&mut out,&a,&b,&mut scratch,top,counts[mode as usize]);
                    assert_eq!(out,expected);
                    if elapsed>=10_000_000{break elapsed;}
                    counts[mode as usize]=counts[mode as usize].checked_mul(2).unwrap();
                };
                println!("{op},{n},{top},{mode},{rep},{},{elapsed}",counts[mode as usize]);
            }}
        }
    }
}
